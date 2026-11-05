from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionState:
    baseline_poverty: bool
    followup_poverty: bool

    @property
    def label(self):
        if not self.baseline_poverty and not self.followup_poverty:
            return "stable_above_poverty"
        if not self.baseline_poverty and self.followup_poverty:
            return "entered_poverty"
        if self.baseline_poverty and not self.followup_poverty:
            return "exited_poverty"
        return "persistent_poverty"


def poverty_transition(baseline_poverty, followup_poverty):
    return TransitionState(
        baseline_poverty=bool(baseline_poverty),
        followup_poverty=bool(followup_poverty),
    ).label
