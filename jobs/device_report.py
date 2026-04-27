from nautobot.extras.jobs import Job


class ActiveDeviceReport(Job):

    class Meta:
        name = "Active Device Report"
        description = "Lists all active devices"
        has_sensitive_variables = False

    def run(self):
        self.logger.info("Job is running successfully!")
