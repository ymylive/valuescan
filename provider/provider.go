package provider

// Provider interface for data providers
type Provider interface {
	GetData() (interface{}, error)
}
