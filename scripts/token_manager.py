#!/usr/bin/env python3
"""
Token Manager for GitLab Deploy Tokens

This module provides functions for encrypting and decrypting GitLab deploy tokens
using symmetric encryption (Fernet).

Usage:
    from token_manager import encrypt_token, decrypt_token

    # Encrypt a token
    encrypted_token, key = encrypt_token("your-deploy-token")
    
    # Decrypt a token
    token = decrypt_token(encrypted_token, key)
"""

import os
import base64
from cryptography.fernet import Fernet

def encrypt_token(token, key=None):
    """
    Encrypt a deploy token using Fernet symmetric encryption.
    
    Args:
        token (str): The deploy token to encrypt
        key (bytes, optional): The encryption key. If not provided, a new key will be generated.
        
    Returns:
        tuple: (encrypted_token, key) - The encrypted token and the encryption key
    """
    if key is None:
        key = Fernet.generate_key()
    elif isinstance(key, str):
        # If key is provided as a string (e.g., from environment variable), encode it
        key = key.encode()
    
    cipher = Fernet(key)
    encrypted_token = cipher.encrypt(token.encode())
    
    return encrypted_token, key

def decrypt_token(encrypted_token, key):
    """
    Decrypt an encrypted deploy token.
    
    Args:
        encrypted_token (bytes or str): The encrypted token
        key (bytes or str): The encryption key
        
    Returns:
        str: The decrypted token
    """
    if isinstance(key, str):
        key = key.encode()
        
    if isinstance(encrypted_token, str):
        encrypted_token = encrypted_token.encode()
        
    cipher = Fernet(key)
    decrypted_token = cipher.decrypt(encrypted_token).decode()
    
    return decrypted_token

def get_auth_headers(username, token):
    """
    Create authentication headers for GitLab API using deploy token.
    
    Args:
        username (str): The deploy token username
        token (str): The deploy token
        
    Returns:
        dict: Headers dictionary with Basic Auth
    """
    auth_str = f"{username}:{token}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    return {"Authorization": f"Basic {encoded_auth}"}

def get_token_from_env():
    """
    Get and decrypt the deploy token from environment variables.
    
    Environment variables:
        ENCRYPTED_DEPLOY_TOKEN: The encrypted deploy token
        ENCRYPTION_KEY: The encryption key
        DEPLOY_TOKEN_USERNAME: The deploy token username
    
    Returns:
        tuple: (username, token, headers) - The username, decrypted token, and auth headers
    """
    encrypted_token = os.environ.get('ENCRYPTED_DEPLOY_TOKEN')
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    username = os.environ.get('DEPLOY_TOKEN_USERNAME')
    
    if not all([encrypted_token, encryption_key, username]):
        raise ValueError(
            "Missing required environment variables: "
            "ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME"
        )
    
    token = decrypt_token(encrypted_token, encryption_key)
    headers = get_auth_headers(username, token)
    
    return username, token, headers