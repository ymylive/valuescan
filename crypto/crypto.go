package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"io"
	"os"
)

// CryptoService handles encryption and decryption
type CryptoService struct {
	key []byte
}

// NewCryptoService creates a new crypto service
func NewCryptoService() (*CryptoService, error) {
	key := os.Getenv("ENCRYPTION_KEY")
	if key == "" {
		// Generate a default key (32 bytes for AES-256)
		key = "default-encryption-key-change-me-32bytes"
	}

	// Ensure key is 32 bytes
	keyBytes := []byte(key)
	if len(keyBytes) < 32 {
		// Pad with zeros
		padded := make([]byte, 32)
		copy(padded, keyBytes)
		keyBytes = padded
	} else if len(keyBytes) > 32 {
		keyBytes = keyBytes[:32]
	}

	return &CryptoService{key: keyBytes}, nil
}

// EncryptForStorage encrypts data for storage
func (c *CryptoService) EncryptForStorage(plaintext string) (string, error) {
	if plaintext == "" {
		return "", nil
	}

	block, err := aes.NewCipher(c.key)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	ciphertext := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	return "enc:" + base64.StdEncoding.EncodeToString(ciphertext), nil
}

// DecryptFromStorage decrypts data from storage
func (c *CryptoService) DecryptFromStorage(encrypted string) (string, error) {
	if encrypted == "" || len(encrypted) < 4 {
		return encrypted, nil
	}

	// Check if it's encrypted
	if encrypted[:4] != "enc:" {
		return encrypted, nil
	}

	data, err := base64.StdEncoding.DecodeString(encrypted[4:])
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(c.key)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return "", errors.New("ciphertext too short")
	}

	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}

// IsEncryptedStorageValue checks if a value is encrypted
func (c *CryptoService) IsEncryptedStorageValue(value string) bool {
	return len(value) >= 4 && value[:4] == "enc:"
}
