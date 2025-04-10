"""
File resource implementation.

This module provides a concrete implementation of the Resource interface
for file operations.
"""
import os
import logging
import random
import time
from typing import Any, Dict, Optional, Union, BinaryIO, TextIO

from ..core import Resource


class FileResource(Resource):
    """
    Resource implementation for file operations.
    
    This class manages file handles, ensuring proper opening,
    reading/writing, and closing of files.
    """
    
    def __init__(
        self,
        filepath: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        buffering: int = -1,
        name: Optional[str] = None,
    ):
        """
        Initialize a file resource.
        
        Args:
            filepath: Path to the file
            mode: File opening mode ('r', 'w', 'a', 'rb', etc.)
            encoding: Text encoding for the file
            buffering: Buffering policy
            name: Optional custom name for the resource
        """
        self._filepath = filepath
        self._mode = mode
        self._encoding = encoding
        self._buffering = buffering
        self._custom_name = name
        self._file_handle = None
        self._logger = logging.getLogger(__name__)
    
    @property
    def name(self) -> str:
        """
        Get the name of the resource.
        
        Returns:
            str: The custom name if provided, otherwise the filename
        """
        if self._custom_name:
            return self._custom_name
        return os.path.basename(self._filepath)
    
    def acquire(self) -> None:
        """
        Open the file.
        
        This method opens the file with the specified mode and options.
        
        Raises:
            FileNotFoundError: If the file doesn't exist (for read modes)
            PermissionError: If the file can't be accessed
            IOError: For other I/O errors
        """
        if self._file_handle is not None:
            self._logger.warning(f"File resource '{self.name}' already acquired")
            return
        
        try:
            self._logger.debug(f"Opening file '{self._filepath}' in mode '{self._mode}'")
            
            # Create parent directories if writing and they don't exist
            if 'w' in self._mode or 'a' in self._mode or '+' in self._mode:
                os.makedirs(os.path.dirname(os.path.abspath(self._filepath)), exist_ok=True)
            
            # Open the file
            self._file_handle = open(
                self._filepath,
                mode=self._mode,
                encoding=self._encoding,
                buffering=self._buffering
            )
            
            self._logger.info(f"File '{self._filepath}' opened successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to open file '{self._filepath}': {e}")
            self._file_handle = None
            raise

    def release(self) -> None:
        """
        Close the file.

        This method ensures the file is properly closed, flushing any buffers.

        Raises:
            IOError: If there's an error closing the file
        """
        if self._file_handle is None:
            self._logger.warning(f"File resource '{self.name}' not acquired")
            return

        # Guard against attempting to close an already closed file
        if self._file_handle.closed:
            self._logger.debug(f"File '{self._filepath}' is already closed")
            self._file_handle = None
            return

        try:
            self._logger.debug(f"Closing file '{self._filepath}'")

            # Safely flush if possible
            try:
                self._file_handle.flush()
            except Exception as flush_error:
                self._logger.debug(f"Could not flush file '{self._filepath}': {flush_error}")

            # Attempt to close
            self._file_handle.close()
            self._file_handle = None
            self._logger.info(f"File '{self._filepath}' closed successfully")

        except Exception as e:
            self._logger.error(f"Error closing file '{self._filepath}': {e}")
            # Ensure our internal state is reset even if close fails
            self._file_handle = None
            raise IOError(f"Error closing file: {e}")
    
    @property
    def is_acquired(self) -> bool:
        """
        Check if the file is currently open.
        
        Returns:
            bool: True if the file is open, False otherwise
        """
        return self._file_handle is not None and not self._file_handle.closed
    
    def read(self, size: Optional[int] = None) -> Union[str, bytes]:
        """
        Read data from the file.
        
        Args:
            size: Optional number of bytes/chars to read (None reads all)
            
        Returns:
            Union[str, bytes]: The data read from the file
            
        Raises:
            RuntimeError: If the file is not open or not opened in read mode
            IOError: If there's an error reading the file
        """
        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        if 'r' not in self._mode and '+' not in self._mode:
            raise RuntimeError(f"File '{self._filepath}' not opened in read mode")
        
        try:
            if size is not None:
                return self._file_handle.read(size)
            else:
                return self._file_handle.read()
                
        except Exception as e:
            self._logger.error(f"Error reading from file '{self._filepath}': {e}")
            raise IOError(f"Error reading from file: {e}")
    
    def write(self, data: Union[str, bytes]) -> int:
        """
        Write data to the file.
        
        Args:
            data: Data to write (str for text mode, bytes for binary mode)
            
        Returns:
            int: Number of bytes/chars written
            
        Raises:
            RuntimeError: If the file is not open or not opened in write mode
            IOError: If there's an error writing to the file
        """

        # Adicionar um pequeno delay para simular processamento
        time.sleep(random.uniform(0.01, 0.05))


        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        if 'w' not in self._mode and 'a' not in self._mode and '+' not in self._mode:
            raise RuntimeError(f"File '{self._filepath}' not opened in write mode")
        
        try:
            return self._file_handle.write(data)
                
        except Exception as e:
            self._logger.error(f"Error writing to file '{self._filepath}': {e}")
            raise IOError(f"Error writing to file: {e}")
    
    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Change the stream position.
        
        Args:
            offset: Offset relative to position indicated by whence
            whence: Position reference (0: start, 1: current, 2: end)
            
        Returns:
            int: The new position
            
        Raises:
            RuntimeError: If the file is not open
            IOError: If there's an error seeking
        """
        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        try:
            return self._file_handle.seek(offset, whence)
                
        except Exception as e:
            self._logger.error(f"Error seeking in file '{self._filepath}': {e}")
            raise IOError(f"Error seeking in file: {e}")
    
    def tell(self) -> int:
        """
        Get the current file position.
        
        Returns:
            int: Current position in the file
            
        Raises:
            RuntimeError: If the file is not open
            IOError: If there's an error getting the position
        """
        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        try:
            return self._file_handle.tell()
                
        except Exception as e:
            self._logger.error(f"Error getting position in file '{self._filepath}': {e}")
            raise IOError(f"Error getting file position: {e}")
    
    def flush(self) -> None:
        """
        Flush the write buffer.
        
        Raises:
            RuntimeError: If the file is not open
            IOError: If there's an error flushing
        """
        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        try:
            self._file_handle.flush()
                
        except Exception as e:
            self._logger.error(f"Error flushing file '{self._filepath}': {e}")
            raise IOError(f"Error flushing file: {e}")
    
    @property
    def file_handle(self) -> Union[TextIO, BinaryIO]:
        """
        Get the underlying file handle.
        
        Returns:
            Union[TextIO, BinaryIO]: The file handle
            
        Raises:
            RuntimeError: If the file is not open
        """
        if not self.is_acquired:
            raise RuntimeError(f"File '{self._filepath}' not open")
        
        return self._file_handle
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource.
        
        Returns:
            Dict[str, Any]: A dictionary containing status information
        """
        status = super().get_status()
        status.update({
            "type": "file",
            "filepath": self._filepath,
            "mode": self._mode,
            "encoding": self._encoding,
            "exists": os.path.exists(self._filepath),
            "size": os.path.getsize(self._filepath) if os.path.exists(self._filepath) else None
        })
        return status