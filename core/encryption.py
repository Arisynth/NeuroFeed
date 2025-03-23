import base64
import os
import hashlib
import platform
import getpass
import logging

logger = logging.getLogger("encryption")

class EncryptionError(Exception):
    """加密或解密过程中发生的错误"""
    pass

def get_machine_key():
    """
    获取基于机器和用户的唯一密钥
    这创建一个独特但一致的密钥，用于简单加密
    """
    # 获取系统和用户信息
    system_info = platform.system() + platform.node() + platform.machine()
    user_info = getpass.getuser()
    
    # 组合信息创建一个唯一的种子
    seed = (system_info + user_info).encode('utf-8')
    
    # 使用SHA-256生成一个固定长度的密钥
    key = hashlib.sha256(seed).hexdigest()
    return key

def encrypt_password(password):
    """
    使用机器特定密钥加密密码
    
    Args:
        password: 要加密的明文密码
        
    Returns:
        加密后的密码字符串
    """
    if not password:
        return ""
        
    try:
        # 获取机器特定密钥
        key = get_machine_key()
        
        # 使用PBKDF2派生一个加密密钥
        derived_key = hashlib.pbkdf2_hmac(
            'sha256', 
            key.encode('utf-8'), 
            b'neurofeed_salt', 
            100000,
            dklen=32
        )
        
        # 简单的XOR加密
        password_bytes = password.encode('utf-8')
        key_bytes = derived_key
        
        # 确保密钥足够长
        while len(key_bytes) < len(password_bytes):
            key_bytes += key_bytes
            
        # 执行XOR操作
        encrypted_bytes = bytes(a ^ b for a, b in zip(password_bytes, key_bytes))
        
        # Base64编码结果
        encrypted = base64.b64encode(encrypted_bytes).decode('utf-8')
        return "encrypted:" + encrypted
        
    except Exception as e:
        logger.error(f"加密密码时出错: {str(e)}")
        # 返回空字符串而不是抛出异常，避免程序崩溃
        return ""

def decrypt_password(encrypted_password):
    """
    解密使用encrypt_password加密的密码
    
    Args:
        encrypted_password: 已加密的密码字符串
        
    Returns:
        解密后的明文密码
    """
    if not encrypted_password:
        return ""
        
    # 检查是否已加密
    if not encrypted_password.startswith("encrypted:"):
        # 可能是旧的未加密密码，直接返回
        return encrypted_password
        
    try:
        # 提取加密部分
        encrypted = encrypted_password[len("encrypted:"):]
        
        # 获取机器特定密钥
        key = get_machine_key()
        
        # 派生加密密钥
        derived_key = hashlib.pbkdf2_hmac(
            'sha256', 
            key.encode('utf-8'), 
            b'neurofeed_salt', 
            100000, 
            dklen=32
        )
        
        # 解码Base64
        encrypted_bytes = base64.b64decode(encrypted)
        key_bytes = derived_key
        
        # 确保密钥足够长
        while len(key_bytes) < len(encrypted_bytes):
            key_bytes += key_bytes
            
        # 执行XOR解密
        decrypted_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, key_bytes))
        
        # 解码为字符串
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        logger.error(f"解密密码时出错: {str(e)}")
        # 返回空字符串而不是抛出异常
        return ""
