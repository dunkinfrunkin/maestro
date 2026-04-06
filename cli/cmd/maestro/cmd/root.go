package cmd

import (
	"github.com/spf13/cobra"
)

var serverURL string

var rootCmd = &cobra.Command{
	Use:   "maestro",
	Short: "Autonomous coding agent orchestration for engineering teams",
	Long: `Maestro manages a pipeline of AI agents that implement, review,
risk-assess, deploy, and monitor code changes — triggered from your
issue tracker.

  maestro login --server https://maestro.yourcompany.com
  maestro status
  maestro tasks
  maestro run <task-id>`,
}

func init() {
	rootCmd.PersistentFlags().StringVar(&serverURL, "server", "", "Maestro server URL")

	rootCmd.AddCommand(versionCmd)
}

func Execute() error {
	return rootCmd.Execute()
}
