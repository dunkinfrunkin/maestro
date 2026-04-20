package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var serveCmd = &cobra.Command{
	Use:   "serve",
	Short: "Start the Maestro server",
	Long:  "Start the Maestro API server, frontend, and nginx proxy in a Docker container.",
	RunE: func(cmd *cobra.Command, args []string) error {
		port, _ := cmd.Flags().GetString("port")

		fmt.Printf("Starting Maestro on port %s...\n", port)
		return dockerRun(
			[]string{"serve", "--host", "0.0.0.0", "--port", "3000"},
			[]string{port + ":3000"},
			nil,
			"",
		)
	},
}

func init() {
	serveCmd.Flags().String("port", "3000", "Port to expose (default: 3000)")
	rootCmd.AddCommand(serveCmd)
}
