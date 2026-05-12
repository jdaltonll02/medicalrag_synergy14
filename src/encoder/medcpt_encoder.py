"""
MedCPT encoder for medical documents and queries
"""

import numpy as np
from typing import List, Union


class MedCPTEncoder:
    """MedCPT encoder for medical domain embeddings"""
    
    def __init__(self, model_name: str = "ncbi/MedCPT-Query-Encoder", device: str = "auto"):
        """
        Initialize MedCPT encoder
        
        Args:
            model_name: HuggingFace model name
            device: Device for inference (cpu/cuda)
        """
        import sys
        self.model_name = model_name
        # Resolve device: 'auto' -> cuda if available else cpu
        if device == "auto":
            try:
                import torch
                cuda_available = torch.cuda.is_available()
                sys.stderr.write(f"[ENCODER] torch.cuda.is_available() = {cuda_available}\n")
                if cuda_available:
                    sys.stderr.write(f"[ENCODER] CUDA device count: {torch.cuda.device_count()}\n")
                    sys.stderr.write(f"[ENCODER] CUDA device name: {torch.cuda.get_device_name(0)}\n")
                sys.stderr.flush()
                self.device = "cuda" if cuda_available else "cpu"
            except Exception as e:
                sys.stderr.write(f"[ENCODER] Error checking CUDA: {e}\n")
                sys.stderr.flush()
                self.device = "cpu"
        else:
            self.device = device
        sys.stderr.write(f"[ENCODER] Using device: {self.device}\n")
        sys.stderr.flush()
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load MedCPT model and tokenizer"""
        import sys
        sys.stderr.write(f"[ENCODER] Loading MedCPT model: {self.model_name} on {self.device}\\n")
        sys.stderr.flush()
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            sys.stderr.write(f"[ENCODER] Loading tokenizer...\\n")
            sys.stderr.flush()
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            sys.stderr.write(f"[ENCODER] Loading model...\\n")
            sys.stderr.flush()
            self.model = AutoModel.from_pretrained(self.model_name)
            sys.stderr.write(f"[ENCODER] Moving model to {self.device}...\n")
            sys.stderr.flush()
            self.model.to(self.device)
            self.model.eval()
            sys.stderr.write(f"[ENCODER] Model loaded successfully\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[ENCODER] ERROR loading model: {e}\n")
            sys.stderr.flush()
            print(f"Warning: Could not load MedCPT model: {e}")
            print("Using placeholder encoder")
            self.model = None
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Encode texts into embeddings
        
        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            normalize: Whether to normalize embeddings
        
        Returns:
            Embeddings array of shape (n_texts, embedding_dim)
        """
        import sys
        sys.stderr.write(f"[ENCODER.encode] Called with {len(texts) if isinstance(texts, list) else 1} texts\n")
        sys.stderr.flush()
        
        if isinstance(texts, str):
            texts = [texts]
        
        if self.model is None:
            # Placeholder: return random embeddings
            embedding_dim = 768
            embeddings = np.random.randn(len(texts), embedding_dim).astype(np.float32)
        else:
            sys.stderr.write(f"[ENCODER.encode] Calling _encode_batch\n")
            sys.stderr.flush()
            embeddings = self._encode_batch(texts, batch_size)
            sys.stderr.write(f"[ENCODER.encode] _encode_batch returned {embeddings.shape}\n")
            sys.stderr.flush()
        
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
        sys.stderr.write(f"[ENCODER.encode] Returning embeddings shape {embeddings.shape}\n")
        sys.stderr.flush()
        return embeddings
    
    def _encode_batch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """Encode texts in batches"""
        import torch
        import logging
        logger = logging.getLogger(__name__)
        
        all_embeddings = []
        num_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            if batch_num % 50 == 0 or batch_num == num_batches:
                logger.info(f"[ENCODER] Processing batch {batch_num}/{num_batches} ({len(all_embeddings) * batch_size}/{len(texts)} texts)")
            
            # Tokenize
            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            # Encode
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use CLS token embedding
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings)
    
    def encode_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a single query
        
        Args:
            query: Query text
            normalize: Whether to normalize embedding
        
        Returns:
            Query embedding (1D array)
        """
        embeddings = self.encode([query], normalize=normalize)
        return embeddings[0]
