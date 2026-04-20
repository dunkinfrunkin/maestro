package cmd

import (
	"fmt"
	"strconv"

	"github.com/spf13/cobra"
)

var workerCmd = &cobra.Command{
	Use:   "worker",
	Short: "Start the agent worker process",
	Long:  "Start a Maestro worker that polls the job queue and runs agent tasks.",
	RunE: func(cmd *cobra.Command, args []string) error {
		concurrency, _ := cmd.Flags().GetInt("concurrency")
		pollInterval, _ := cmd.Flags().GetFloat64("poll-interval")

		fmt.Printf("Starting worker (concurrency=%d, poll=%.1fs)...\n", concurrency, pollInterval)

		containerArgs := []string{
			"worker",
			"--concurrency", strconv.Itoa(concurrency),
			"--poll-interval", strconv.FormatFloat(pollInterval, 'f', 1, 64),
		}

		return dockerRun(
			containerArgs,
			nil,
			map[string]string{"MAESTRO_WORKER_MODE": "queue"},
			"",
		)
	},
}

func init() {
	workerCmd.Flags().Int("concurrency", 3, "Max concurrent agent jobs (default: 3)")
	workerCmd.Flags().Float64("poll-interval", 2.0, "Seconds between job polls (default: 2.0)")
	rootCmd.AddCommand(workerCmd)
}
