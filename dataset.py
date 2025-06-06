"""Module for handling bilingual datasets for transformer-based translation tasks.

This module includes the `BillingualDataset` class, which prepares and processes
parallel text data for training and evaluation.
"""
import torch
from torch.utils.data import Dataset
from tokenizers import Tokenizer

class BillingualDataset(Dataset):
    """A PyTorch Dataset class for handling bilingual translation data.

    This class processes source and target language pairs, tokenizes them, and prepares
    them for input into a transformer model. It handles padding, masking, and special tokens.

    Args:
        ds: The raw dataset containing parallel translations.
        tokenizer_src (Tokenizer): Tokenizer for the source language.
        tokenizer_tgt (Tokenizer): Tokenizer for the target language.
        src_lang (str): Source language identifier.
        tgt_lang (str): Target language identifier.
        seq_len (int): Maximum sequence length for padding/truncation.

    Attributes:
        sos_token (torch.Tensor): Start-of-sequence token tensor.
        eos_token (torch.Tensor): End-of-sequence token tensor.
        pad_token (torch.Tensor): Padding token tensor.
    """

    def __init__(self, ds, tokenizer_src: Tokenizer, tokenzier_tgt: Tokenizer, src_lang, tgt_lang, seq_len) -> None:
        super().__init__()
        self.ds = ds
        self.tokenizer_src = tokenizer_src
        self.tokenzier_tgt = tokenzier_tgt
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.seq_len = seq_len

        self.sos_token = torch.tensor([tokenizer_src.token_to_id('[SOS]')], dtype=torch.int64)
        self.eos_token = torch.tensor([tokenizer_src.token_to_id('[EOS]')], dtype=torch.int64)
        self.pad_token = torch.tensor([tokenizer_src.token_to_id('[PAD]')], dtype=torch.int64)

    def __len__(self):
        return len(self.ds)
    
    def __getitem__(self, index):
        src_target_pair = self.ds[index]
        src_text = src_target_pair['translation'][self.src_lang]
        tgt_text = src_target_pair['translation'][self.tgt_lang]

        enc_input_tokens = self.tokenizer_src.encode(src_text).ids
        dec_input_tokens = self.tokenzier_tgt.encode(tgt_text).ids

        enc_num_padding_tokens = self.seq_len - len(enc_input_tokens) - 2
        dec_num_padding_tokens = self.seq_len - len(dec_input_tokens) - 1

        if enc_num_padding_tokens < 0 or dec_num_padding_tokens < 0:
            raise ValueError('Sentence is too long')      
        encoder_input = torch.concat([
            self.sos_token,
            torch.tensor(enc_input_tokens, dtype=torch.int64),
            self.eos_token,
            torch.tensor([self.pad_token] * enc_num_padding_tokens, dtype=torch.int64)
        ])

        decoder_input = torch.concat([
            self.sos_token,
            torch.tensor(dec_input_tokens, dtype=torch.int64),
            torch.tensor([self.pad_token] * dec_num_padding_tokens, dtype=torch.int64)
        ])
        
        label = torch.cat([
            torch.tensor(dec_input_tokens, dtype=torch.int64),
            self.eos_token,
            torch.tensor([self.pad_token] * dec_num_padding_tokens, dtype=torch.int64)
        ])

        assert encoder_input.size(0) == self.seq_len
        assert decoder_input.size(0) == self.seq_len
        assert label.size(0) == self.seq_len

        return {
            'encoder_input': encoder_input, # {seq_len}
            'decoder_input': decoder_input, # (seq_len)
            'encoder_mask': (encoder_input !=self.pad_token).unsqueeze(0).unsqueeze(0).int(),
            'decoder_mask': (decoder_input !=self.pad_token).unsqueeze(0).unsqueeze(0).int() & causal_mask(decoder_input.size(0)),  # (1,1 ,Seq_len) & (1, SeqLen, Seq_len)
            'label': label,
            'src_text': src_text,
            'tgt_text': tgt_text
        }
 
def causal_mask(size):
    """Creates a causal mask to prevent attention to future positions in the decoder.

    Args:
        size (int): Size of the mask (sequence length).

    Returns:
        torch.Tensor: A boolean mask where future positions are masked (False).
    """
    mask = torch.triu(torch.ones(1 ,size, size), diagonal=1).type(torch.int)
    return mask == 0
