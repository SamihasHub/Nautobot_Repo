from nautobot.apps.jobs import Job, register_jobs
from nautobot.circuits.models import Circuit


class CircuitStatusReport(Job):

    class Meta:
        name = "3. Circuit Status Report"
        description = "Active vs decommissioned circuits breakdown"
        has_sensitive_variables = False

    def run(self):
        circuits = Circuit.objects.all()
        if not circuits.exists():
            self.logger.warning("No circuits found!")
            return
        active = 0
        decommissioned = 0
        provisioning = 0
        other = 0
        for circuit in circuits:
            status = circuit.status.name if circuit.status else "Unknown"
            provider = circuit.provider.name if circuit.provider else "Unknown"
            ctype = circuit.circuit_type.name if circuit.circuit_type else "Unknown"
            if status == "Active":
                active += 1
                self.logger.info(
                    f"[ACTIVE] {circuit.cid} | Provider: {provider} | Type: {ctype}"
                )
            elif status == "Decommissioned":
                decommissioned += 1
                self.logger.warning(
                    f"[DECOMMISSIONED] {circuit.cid} | Provider: {provider} | Type: {ctype}"
                )
            elif status == "Provisioning":
                provisioning += 1
                self.logger.info(
                    f"[PROVISIONING] {circuit.cid} | Provider: {provider} | Type: {ctype}"
                )
            else:
                other += 1
                self.logger.info(
                    f"[{status.upper()}] {circuit.cid} | Provider: {provider}"
                )
        self.logger.info(
            f"SUMMARY — Active: {active} | Provisioning: {provisioning} | "
            f"Decommissioned: {decommissioned} | Other: {other}"
        )


register_jobs(CircuitStatusReport)
