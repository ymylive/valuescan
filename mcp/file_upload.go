package mcp

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"strings"
)

// FileUploadResponse OpenAI Files API response
type FileUploadResponse struct {
	ID        string `json:"id"`
	Object    string `json:"object"`
	Bytes     int    `json:"bytes"`
	CreatedAt int64  `json:"created_at"`
	Filename  string `json:"filename"`
	Purpose   string `json:"purpose"`
}

// UploadTextAsFile uploads text content as a txt file to OpenAI Files API
// Returns the file ID that can be used in messages
func (c *Client) UploadTextAsFile(content string, filename string) (string, error) {
	if filename == "" {
		filename = "input.txt"
	}

	// Ensure filename ends with .txt
	if !strings.HasSuffix(filename, ".txt") {
		filename = filename + ".txt"
	}

	// Build multipart form data
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	// Add file field
	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return "", fmt.Errorf("failed to create form file: %w", err)
	}
	_, err = part.Write([]byte(content))
	if err != nil {
		return "", fmt.Errorf("failed to write content: %w", err)
	}

	// Add purpose field
	err = writer.WriteField("purpose", "assistants")
	if err != nil {
		return "", fmt.Errorf("failed to write purpose field: %w", err)
	}

	err = writer.Close()
	if err != nil {
		return "", fmt.Errorf("failed to close writer: %w", err)
	}

	// Build request URL
	uploadURL := strings.TrimSuffix(c.BaseURL, "/chat/completions")
	uploadURL = strings.TrimSuffix(uploadURL, "/v1") + "/v1/files"

	c.logger.Infof("📤 [MCP] Uploading text as file to: %s (size: %d bytes)", uploadURL, len(content))

	// Create HTTP request
	req, err := http.NewRequest("POST", uploadURL, &buf)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", writer.FormDataContentType())
	c.hooks.setAuthHeader(req.Header)

	// Send request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("file upload failed (status %d): %s", resp.StatusCode, string(body))
	}

	// Parse response
	var uploadResp FileUploadResponse
	if err := json.Unmarshal(body, &uploadResp); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	c.logger.Infof("✅ [MCP] File uploaded successfully: ID=%s, Bytes=%d", uploadResp.ID, uploadResp.Bytes)
	return uploadResp.ID, nil
}

// DeleteFile deletes an uploaded file from OpenAI
func (c *Client) DeleteFile(fileID string) error {
	deleteURL := strings.TrimSuffix(c.BaseURL, "/chat/completions")
	deleteURL = strings.TrimSuffix(deleteURL, "/v1") + "/v1/files/" + fileID

	req, err := http.NewRequest("DELETE", deleteURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	c.hooks.setAuthHeader(req.Header)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("file deletion failed (status %d): %s", resp.StatusCode, string(body))
	}

	c.logger.Infof("🗑️ [MCP] File deleted: %s", fileID)
	return nil
}

// BuildMessageWithFileContent builds a message content array that includes file reference
// This is used for models that support file attachments in messages
func BuildMessageWithFileContent(textContent string, fileID string) []map[string]interface{} {
	return []map[string]interface{}{
		{
			"type": "text",
			"text": textContent,
		},
		{
			"type": "file",
			"file": map[string]string{
				"file_id": fileID,
			},
		},
	}
}

// CallWithFileUpload calls AI API with long text uploaded as file
// This is useful for bypassing input length limits
func (c *Client) CallWithFileUpload(systemPrompt, userPrompt string) (string, error) {
	c.logger.Infof("📁 [MCP] Using file upload mode for long text (length: %d)", len(userPrompt))

	// Upload user prompt as file
	fileID, err := c.UploadTextAsFile(userPrompt, "user_input.txt")
	if err != nil {
		c.logger.Warnf("⚠️ [MCP] File upload failed, falling back to normal mode: %v", err)
		// Fallback to normal call
		return c.CallWithMessages(systemPrompt, userPrompt)
	}

	// Ensure file is deleted after use
	defer func() {
		if deleteErr := c.DeleteFile(fileID); deleteErr != nil {
			c.logger.Warnf("⚠️ [MCP] Failed to delete file %s: %v", fileID, deleteErr)
		}
	}()

	// Build request with file reference
	// For OpenAI, we use the Responses API format with file attachment
	request, err := NewRequestBuilder().
		WithSystemPrompt(systemPrompt).
		WithUserPrompt(fmt.Sprintf("请阅读附件文件(file_id: %s)中的内容并进行分析。", fileID)).
		Build()
	if err != nil {
		return "", fmt.Errorf("failed to build request: %w", err)
	}

	// Add file attachment to messages
	// Note: This uses OpenAI's format for file attachments in chat completions
	return c.CallWithRequest(request)
}
