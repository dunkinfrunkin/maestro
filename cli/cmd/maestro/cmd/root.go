package cmd

import (
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "maestro",
	Short: "Autonomous coding agent orchestration for engineering teams",
	Long: `Maestro manages a pipeline of AI agents that implement, review,
risk-assess, deploy, and monitor code changes — triggered from your
issue tracker.

  maestro app                    Start the full application (Docker)
  maestro serve                  Start the API server (Docker)
  maestro worker                 Start a worker process (Docker)
  maestro init                   Initialize ~/.maestro/config.yaml
  maestro repo init              Scaffold .agents/ templates`,
}

func init() {
	rootCmd.AddCommand(versionCmd)
}

func Execute() error {
	return rootCmd.Execute()
}
