package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var appCmd = &cobra.Command{
	Use:   "app",
	Short: "Start the full Maestro application (API + frontend)",
	Long: `Start the full Maestro stack in a single Docker container:
  - PostgreSQL connection (external or provide DATABASE_URL)
  - Backend API server
  - Frontend (Next.js)
  - Nginx reverse proxy

Equivalent to 'maestro serve' but also runs database migrations on startup.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		port, _ := cmd.Flags().GetString("port")

		fmt.Printf("Starting Maestro app on port %s...\n", port)
		return dockerRun(
			nil,
			[]string{port + ":3000"},
			nil,
			"",
		)
	},
}

func init() {
	appCmd.Flags().String("port", "3000", "Port to expose (default: 3000)")
	rootCmd.AddCommand(appCmd)
}
