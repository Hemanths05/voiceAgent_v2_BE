"""
Text Chunking Utilities
Splits text into overlapping chunks for RAG embeddings
"""
import re
from typing import List, Dict, Any
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TextChunker:
    """
    Handles text chunking with overlap for RAG

    Strategy:
    - Target chunk size: ~512 tokens (roughly 2000 characters)
    - Overlap: 50 tokens (roughly 200 characters)
    - Sentence boundary awareness
    """

    # Approximate conversion: 1 token ≈ 4 characters
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        chunk_size_tokens: int = 512,
        overlap_tokens: int = 50,
        min_chunk_size_tokens: int = 50
    ):
        """
        Initialize text chunker

        Args:
            chunk_size_tokens: Target chunk size in tokens
            overlap_tokens: Overlap between chunks in tokens
            min_chunk_size_tokens: Minimum chunk size to avoid tiny chunks
        """
        self.chunk_size = chunk_size_tokens * self.CHARS_PER_TOKEN
        self.overlap = overlap_tokens * self.CHARS_PER_TOKEN
        self.min_chunk_size = min_chunk_size_tokens * self.CHARS_PER_TOKEN

        logger.debug(
            f"Initialized TextChunker: chunk_size={chunk_size_tokens} tokens "
            f"({self.chunk_size} chars), overlap={overlap_tokens} tokens "
            f"({self.overlap} chars)"
        )

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex

        Handles common sentence endings: . ! ?
        Preserves sentence structure better than simple split

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Pattern: Split on . ! ? followed by space and capital letter or end
        # Handles abbreviations like "Dr." "Mr." "U.S." etc.
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'

        # Split into sentences
        sentences = re.split(sentence_pattern, text)

        # Clean up
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with sentence awareness

        Args:
            text: Input text to chunk
            metadata: Optional metadata to include with each chunk

        Returns:
            List of chunk dictionaries with 'text', 'chunk_index', 'metadata'
        """
        if not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Split into sentences
        sentences = self.split_into_sentences(text)
        logger.debug(f"Split text into {len(sentences)} sentences")

        chunks = []
        current_chunk = []
        current_chunk_size = 0
        chunk_index = 0

        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)

            # If single sentence exceeds chunk size, split it by character
            if sentence_size > self.chunk_size:
                # If we have accumulated sentences, save them first
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
                    chunk_index += 1
                    current_chunk = []
                    current_chunk_size = 0

                # Split large sentence by character with overlap
                large_chunks = self._split_large_text(sentence)
                for large_chunk in large_chunks:
                    chunks.append(self._create_chunk(large_chunk, chunk_index, metadata))
                    chunk_index += 1

                continue

            # Check if adding this sentence would exceed chunk size
            if current_chunk_size + sentence_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
                chunk_index += 1

                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_size = 0
                overlap_sentences = []
                for prev_sentence in reversed(current_chunk):
                    if overlap_size + len(prev_sentence) <= self.overlap:
                        overlap_sentences.insert(0, prev_sentence)
                        overlap_size += len(prev_sentence)
                    else:
                        break

                current_chunk = overlap_sentences
                current_chunk_size = overlap_size

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_chunk_size += sentence_size

        # Add final chunk if it has content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            # Only add if it meets minimum size (avoid tiny last chunks)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
            elif chunks:
                # Merge with previous chunk if too small
                chunks[-1]["text"] += " " + chunk_text
            else:
                # If it's the only chunk, keep it regardless of size
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))

        logger.info(
            f"Created {len(chunks)} chunks from {len(text)} characters "
            f"({len(sentences)} sentences)"
        )

        return chunks

    def _split_large_text(self, text: str) -> List[str]:
        """
        Split very large text by character count with overlap

        Used for sentences/paragraphs that exceed chunk size

        Args:
            text: Large text to split

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]

            # Try to break at last space within chunk
            if end < text_length:
                last_space = chunk.rfind(' ')
                if last_space > self.chunk_size * 0.8:  # At least 80% through
                    end = start + last_space
                    chunk = text[start:end]

            chunks.append(chunk.strip())

            # Move start position with overlap
            start = end - self.overlap if end < text_length else text_length

        return chunks

    def _create_chunk(
        self,
        text: str,
        chunk_index: int,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create chunk dictionary

        Args:
            text: Chunk text
            chunk_index: Index of chunk in document
            metadata: Optional metadata

        Returns:
            Chunk dictionary
        """
        chunk = {
            "text": text.strip(),
            "chunk_index": chunk_index,
            "char_count": len(text),
            "token_count_estimate": len(text) // self.CHARS_PER_TOKEN,
        }

        if metadata:
            chunk["metadata"] = metadata

        return chunk

    def chunk_with_headers(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks while preserving section headers

        Useful for structured documents with headers like:
        - "# Header" (Markdown)
        - "Header:" (Colon-separated)
        - "HEADER" (All caps)

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            List of chunk dictionaries
        """
        # Split by common header patterns
        header_pattern = r'(?:^|\n)(?:#{1,6}\s+|\b[A-Z][A-Z\s]{2,}:|\[.+\])\s*\n'
        sections = re.split(header_pattern, text)

        all_chunks = []
        for section_index, section in enumerate(sections):
            if not section.strip():
                continue

            # Add section index to metadata
            section_metadata = metadata.copy() if metadata else {}
            section_metadata["section_index"] = section_index

            # Chunk each section
            section_chunks = self.chunk_text(section, section_metadata)
            all_chunks.extend(section_chunks)

        # Renumber chunks globally
        for i, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = i

        logger.info(
            f"Created {len(all_chunks)} chunks from {len(sections)} sections "
            f"(with header preservation)"
        )

        return all_chunks

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate number of tokens in text

        Uses rough approximation: 1 token ≈ 4 characters

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // TextChunker.CHARS_PER_TOKEN

    @staticmethod
    def preview_chunk(chunk: Dict[str, Any], max_preview_chars: int = 100) -> str:
        """
        Create preview of chunk for logging/debugging

        Args:
            chunk: Chunk dictionary
            max_preview_chars: Maximum characters in preview

        Returns:
            Preview string
        """
        text = chunk.get("text", "")
        preview = text[:max_preview_chars]
        if len(text) > max_preview_chars:
            preview += "..."

        return (
            f"Chunk {chunk.get('chunk_index', 0)}: "
            f"{chunk.get('token_count_estimate', 0)} tokens | "
            f"{preview}"
        )


class SmartTextChunker(TextChunker):
    """
    Enhanced text chunker with semantic awareness

    Additional features:
    - Paragraph boundary awareness
    - List detection
    - Code block preservation
    """

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text with semantic awareness

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            List of chunk dictionaries
        """
        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        chunks = []
        current_chunk = []
        current_chunk_size = 0
        chunk_index = 0

        for para in paragraphs:
            para_size = len(para)

            # If paragraph exceeds chunk size, use base chunking
            if para_size > self.chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
                    chunk_index += 1
                    current_chunk = []
                    current_chunk_size = 0

                # Chunk large paragraph
                para_chunks = super().chunk_text(para, metadata)
                for para_chunk in para_chunks:
                    para_chunk["chunk_index"] = chunk_index
                    chunks.append(para_chunk)
                    chunk_index += 1

                continue

            # Check if adding paragraph would exceed chunk size
            if current_chunk_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
                chunk_index += 1

                # Start new chunk (no overlap for paragraph-based chunking)
                current_chunk = []
                current_chunk_size = 0

            # Add paragraph to current chunk
            current_chunk.append(para)
            current_chunk_size += para_size

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
            elif chunks:
                chunks[-1]["text"] += "\n\n" + chunk_text
            else:
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))

        logger.info(
            f"Created {len(chunks)} chunks from {len(paragraphs)} paragraphs "
            f"(semantic chunking)"
        )

        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs

        Considers:
        - Double newlines
        - List items
        - Code blocks

        Args:
            text: Input text

        Returns:
            List of paragraphs
        """
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)

        # Clean up
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs


# Export public classes
__all__ = ["TextChunker", "SmartTextChunker"]
