package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var defaultConfig = `# Maestro Configuration
# Env vars override these values. Generate with: maestro init
# Docs: https://github.com/dunkinfrunkin/maestro

server:
  host: 127.0.0.1
  port: 8000

frontend:
  port: 3000

worker:
  concurrency: 3
  poll_interval: 2.0
  mode: inline          # "inline" = agents run in API process, "queue" = workers pick up jobs

database:
  url: ""               # e.g. postgresql+asyncpg://user:pass@host:5432/db

auth:
  secret: ""            # Required. Generate with: openssl rand -hex 32
  disabled: false       # Set true to skip auth (dev only)
  oidc_issuer: ""       # e.g. https://yourcompany.okta.com/oauth2/default
  oidc_client_id: ""
  oidc_client_secret: ""

encryption:
  key: ""               # Fernet key for encrypting stored tokens

frontend_url: ""        # e.g. http://localhost:3000

# API keys (can also be set per-workspace in Settings > Models)
anthropic:
  api_key: ""

openai:
  api_key: ""
`

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize ~/.maestro/config.yaml",
	RunE: func(cmd *cobra.Command, args []string) error {
		force, _ := cmd.Flags().GetBool("force")

		home, err := os.UserHomeDir()
		if err != nil {
			return err
		}
		dir := filepath.Join(home, ".maestro")
		configPath := filepath.Join(dir, "config.yaml")

		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}

		if _, err := os.Stat(configPath); err == nil && !force {
			fmt.Printf("Config already exists: %s\n", configPath)
			fmt.Println("Use --force to overwrite.")
			return nil
		}

		if err := os.WriteFile(configPath, []byte(defaultConfig), 0o644); err != nil {
			return err
		}
		fmt.Printf("Created %s\n", configPath)
		fmt.Println("Edit the file to configure your Maestro instance.")
		return nil
	},
}

func init() {
	initCmd.Flags().Bool("force", false, "Overwrite existing config")
	rootCmd.AddCommand(initCmd)
}
