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
		filename = "trading_data.txt"
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

	// Add purpose field (for assistants)
	err = writer.WriteField("purpose", "assistants")
	if err != nil {
		return "", fmt.Errorf("failed to write purpose field: %w", err)
	}

	err = writer.Close()
	if err != nil {
		return "", fmt.Errorf("failed to close writer: %w", err)
	}

	// Build request URL - convert chat/completions URL to files URL
	uploadURL := c.BaseURL
	uploadURL = strings.TrimSuffix(uploadURL, "/chat/completions")
	uploadURL = strings.TrimSuffix(uploadURL, "/v1")
	uploadURL = uploadURL + "/v1/files"

	c.logger.Infof("📤 [%s] Uploading text as file to: %s (size: %d bytes)", c.String(), uploadURL, len(content))

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

	c.logger.Infof("✅ [%s] File uploaded successfully: ID=%s, Bytes=%d", c.String(), uploadResp.ID, uploadResp.Bytes)
	return uploadResp.ID, nil
}

// DeleteFile deletes an uploaded file from OpenAI
func (c *Client) DeleteFile(fileID string) error {
	deleteURL := c.BaseURL
	deleteURL = strings.TrimSuffix(deleteURL, "/chat/completions")
	deleteURL = strings.TrimSuffix(deleteURL, "/v1")
	deleteURL = deleteURL + "/v1/files/" + fileID

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

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("file deletion failed (status %d): %s", resp.StatusCode, string(body))
	}

	c.logger.Infof("🗑️ [%s] File deleted: %s", c.String(), fileID)
	return nil
}

// CallWithFileUpload calls AI API with long text uploaded as file
// This is useful for bypassing input length limits
func (c *Client) CallWithFileUpload(systemPrompt, userPrompt string) (string, error) {
	c.logger.Infof("📁 [%s] Using file upload mode for long text (length: %d chars)", c.String(), len(userPrompt))

	// Upload user prompt as file
	fileID, err := c.UploadTextAsFile(userPrompt, "trading_data.txt")
	if err != nil {
		c.logger.Warnf("⚠️ [%s] File upload failed: %v, falling back to direct content", c.String(), err)
		// Fallback to direct content if file upload fails
		return c.callWithDirectContent(systemPrompt, userPrompt)
	}

	// Ensure file is deleted after use
	defer func() {
		if deleteErr := c.DeleteFile(fileID); deleteErr != nil {
			c.logger.Warnf("⚠️ [%s] Failed to delete file %s: %v", c.String(), fileID, deleteErr)
		}
	}()

	// Build messages with file attachment
	var messages []any

	if systemPrompt != "" {
		messages = append(messages, map[string]string{
			"role":    "system",
			"content": systemPrompt,
		})
	}

	// Create user message with file attachment reference
	userMessage := map[string]any{
		"role": "user",
		"content": []map[string]any{
			{
				"type": "text",
				"text": "Please analyze the trading data in the attached file and provide your trading decision.",
			},
			{
				"type": "file",
				"file": map[string]string{
					"file_id": fileID,
				},
			},
		},
	}
	messages = append(messages, userMessage)

	// Build request body
	requestBody := map[string]any{
		"model":       c.Model,
		"messages":    messages,
		"temperature": c.config.Temperature,
	}

	if c.Provider == ProviderOpenAI {
		requestBody["max_completion_tokens"] = c.MaxTokens
	} else {
		requestBody["max_tokens"] = c.MaxTokens
	}

	c.logger.Infof("📤 [%s] Sending request with file attachment (file_id: %s)", c.String(), fileID)

	// Send request
	return c.sendRequest(requestBody)
}

// callWithDirectContent sends content directly without file upload (fallback)
func (c *Client) callWithDirectContent(systemPrompt, userPrompt string) (string, error) {
	var messages []any

	if systemPrompt != "" {
		messages = append(messages, map[string]string{
			"role":    "system",
			"content": systemPrompt,
		})
	}

	messages = append(messages, map[string]string{
		"role":    "user",
		"content": userPrompt,
	})

	requestBody := map[string]any{
		"model":       c.Model,
		"messages":    messages,
		"temperature": c.config.Temperature,
	}

	if c.Provider == ProviderOpenAI {
		requestBody["max_completion_tokens"] = c.MaxTokens
	} else {
		requestBody["max_tokens"] = c.MaxTokens
	}

	c.logger.Infof("📤 [%s] Sending request with direct content (%d chars)", c.String(), len(userPrompt))
	return c.sendRequest(requestBody)
}

// sendRequest sends the request body to the AI API
func (c *Client) sendRequest(requestBody map[string]any) (string, error) {
	jsonBody, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := c.BaseURL
	if !c.UseFullURL && !strings.HasSuffix(url, "/chat/completions") {
		url = strings.TrimSuffix(url, "/") + "/chat/completions"
	}

	req, err := http.NewRequest("POST", url, bytes.NewReader(jsonBody))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	c.hooks.setAuthHeader(req.Header)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API returned error (status %d): %s", resp.StatusCode, string(body))
	}

	// Parse response
	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	if len(result.Choices) == 0 {
		return "", fmt.Errorf("no choices in response")
	}

	return result.Choices[0].Message.Content, nil
}
