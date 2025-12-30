package experience

var installationID string

// SetInstallationID sets the installation ID
func SetInstallationID(id string) {
	installationID = id
}

// GetInstallationID returns the installation ID
func GetInstallationID() string {
	return installationID
}
