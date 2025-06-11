import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.file_upload import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentSplitter:
    """Service for intelligently splitting large documents into chunks"""
    
    def __init__(self):
        # Patterns for detecting document structure
        self.header_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(.+)\n[=\-]{3,}$',  # Text headers with underlines
            r'^\d+\.?\s+(.+)$',  # Numbered sections
            r'^[A-Z][A-Z\s]{2,}$',  # ALL CAPS headers
            r'^Chapter\s+\d+',  # Chapter headers
            r'^Section\s+\d+',  # Section headers
        ]
        
        # Sentence ending patterns
        self.sentence_endings = r'[.!?]+\s+'
        
        # Paragraph boundaries
        self.paragraph_boundary = r'\n\s*\n'
    
    def detect_document_structure(self, text: str) -> Dict[str, List[int]]:
        """Detect headers, paragraphs, and other structural elements"""
        lines = text.split('\n')
        structure = {
            'headers': [],
            'paragraphs': [],
            'sentences': [],
            'code_blocks': [],
            'lists': []
        }
        
        current_pos = 0
        in_code_block = False
        
        for i, line in enumerate(lines):
            line_start = current_pos
            current_pos += len(line) + 1  # +1 for newline
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Code blocks
            if '```' in line or line.strip().startswith('    '):
                if '```' in line:
                    in_code_block = not in_code_block
                if in_code_block:
                    structure['code_blocks'].append(line_start)
                continue
            
            # Headers
            for pattern in self.header_patterns:
                if re.match(pattern, line.strip(), re.MULTILINE):
                    structure['headers'].append(line_start)
                    break
            
            # Lists
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                structure['lists'].append(line_start)
        
        # Find paragraph boundaries
        for match in re.finditer(self.paragraph_boundary, text):
            structure['paragraphs'].append(match.start())
        
        # Find sentence boundaries
        for match in re.finditer(self.sentence_endings, text):
            structure['sentences'].append(match.end())
        
        return structure
    
    def find_optimal_split_points(
        self, 
        text: str, 
        max_chunk_size: int, 
        overlap: int,
        structure: Dict[str, List[int]]
    ) -> List[int]:
        """Find optimal points to split the document"""
        split_points = [0]  # Start with beginning
        text_length = len(text)
        
        current_pos = 0
        
        while current_pos < text_length:
            # Calculate target end position
            target_end = min(current_pos + max_chunk_size, text_length)
            
            if target_end >= text_length:
                # Last chunk
                split_points.append(text_length)
                break
            
            # Find the best split point near target_end
            best_split = self._find_best_split_point(
                text, current_pos, target_end, structure
            )
            
            split_points.append(best_split)
            
            # Move to next position with overlap
            current_pos = max(best_split - overlap, current_pos + 1)
        
        return split_points
    
    def _find_best_split_point(
        self,
        text: str,
        start: int,
        target_end: int,
        structure: Dict[str, List[int]]
    ) -> int:
        """Find the best split point near target_end"""
        # Priority order: paragraph > sentence > word > character
        search_window = min(200, (target_end - start) // 4)  # Look within 200 chars
        
        # Look for paragraph boundaries first
        for pos in reversed(structure['paragraphs']):
            if target_end - search_window <= pos <= target_end:
                return pos
        
        # Look for sentence boundaries
        for pos in reversed(structure['sentences']):
            if target_end - search_window <= pos <= target_end:
                return pos
        
        # Fall back to word boundaries
        for i in range(target_end, max(start, target_end - search_window), -1):
            if i < len(text) and text[i].isspace():
                return i
        
        # Last resort: character boundary
        return target_end
    
    def split_document(
        self,
        content: str,
        title: str,
        max_chunk_size: int = 5000,
        chunk_overlap: int = 200,
        preserve_structure: bool = True,
        source: Optional[str] = None,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Split a document into optimal chunks"""
        
        if not content.strip():
            return []
        
        # Clean the content
        content = self._clean_content(content)
        
        # If document is small enough, return as single chunk
        if len(content) <= max_chunk_size:
            return [DocumentChunk(
                title=title,
                content=content,
                chunk_index=0,
                total_chunks=1,
                source=source,
                document_type=document_type,
                metadata={
                    **(metadata or {}),
                    'is_complete_document': True,
                    'original_length': len(content)
                }
            )]
        
        # Detect document structure if preserving structure
        structure = {}
        if preserve_structure:
            structure = self.detect_document_structure(content)
        
        # Find optimal split points
        split_points = self.find_optimal_split_points(
            content, max_chunk_size, chunk_overlap, structure
        )
        
        # Create chunks
        chunks = []
        for i in range(len(split_points) - 1):
            start_pos = split_points[i]
            end_pos = split_points[i + 1]
            
            chunk_content = content[start_pos:end_pos].strip()
            
            if not chunk_content:
                continue
            
            # Generate chunk title
            chunk_title = self._generate_chunk_title(
                title, chunk_content, i, len(split_points) - 1
            )
            
            # Prepare chunk metadata
            chunk_metadata = {
                **(metadata or {}),
                'chunk_start': start_pos,
                'chunk_end': end_pos,
                'original_length': len(content),
                'chunk_length': len(chunk_content),
                'overlap_with_previous': chunk_overlap if i > 0 else 0
            }
            
            chunks.append(DocumentChunk(
                title=chunk_title,
                content=chunk_content,
                chunk_index=i,
                total_chunks=len(split_points) - 1,
                source=source,
                document_type=document_type,
                metadata=chunk_metadata
            ))
        
        logger.info(f"Split document '{title}' into {len(chunks)} chunks")
        return chunks
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r' +', ' ', content)  # Multiple spaces to single space
        content = content.strip()
        
        return content
    
    def _generate_chunk_title(
        self, 
        original_title: str, 
        chunk_content: str, 
        chunk_index: int, 
        total_chunks: int
    ) -> str:
        """Generate appropriate title for a chunk"""
        
        if total_chunks == 1:
            return original_title
        
        # Try to find a good title from the chunk content
        lines = chunk_content.split('\n')
        
        # Look for headers in the first few lines
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            
            # Check if it looks like a header
            for pattern in self.header_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    header_text = match.group(1) if match.groups() else line
                    return f"{original_title} - {header_text}"
        
        # Fall back to part numbering
        return f"{original_title} - Part {chunk_index + 1}"
    
    def estimate_chunks(self, content: str, max_chunk_size: int) -> Dict[str, Any]:
        """Estimate how many chunks a document would be split into"""
        content_length = len(content)
        
        if content_length <= max_chunk_size:
            return {
                'estimated_chunks': 1,
                'content_length': content_length,
                'average_chunk_size': content_length,
                'requires_splitting': False
            }
        
        # Rough estimate
        estimated_chunks = (content_length + max_chunk_size - 1) // max_chunk_size
        average_chunk_size = content_length / estimated_chunks
        
        return {
            'estimated_chunks': estimated_chunks,
            'content_length': content_length,
            'average_chunk_size': int(average_chunk_size),
            'requires_splitting': True
        }
    
    def merge_chunks(self, chunks: List[DocumentChunk], separator: str = "\n\n") -> str:
        """Merge chunks back into a single document"""
        return separator.join(chunk.content for chunk in chunks)


# Global instance
document_splitter = DocumentSplitter() 