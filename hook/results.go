package hook

import "net/http"

// SetHttpClientResult is hook return payload for SET_HTTP_CLIENT.
type SetHttpClientResult struct {
	result *http.Client
	err    error
}

// NewSetHttpClientResult constructs hook result.
func NewSetHttpClientResult(client *http.Client, err error) *SetHttpClientResult {
	return &SetHttpClientResult{
		result: client,
		err:    err,
	}
}

// Error returns hook execution error.
func (r *SetHttpClientResult) Error() error {
	if r == nil {
		return nil
	}
	return r.err
}

// GetResult returns injected HTTP client.
func (r *SetHttpClientResult) GetResult() *http.Client {
	if r == nil {
		return nil
	}
	return r.result
}
