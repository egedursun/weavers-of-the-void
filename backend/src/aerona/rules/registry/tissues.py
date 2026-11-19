from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.BODY


@dataclass(frozen=True)
class TissueRules(Spanned):
    depth_per_severity: int = rule(18, 0, 100, G, "Force behind a wound of each severity when no weapon is known, against tissue yields")
    tissue_spend_pct: int = rule(60, 0, 200, G, "Force a strike spends on each tissue it passes, per point of that tissue's yield (%)")
    tendon_loss: int = rule(60, 0, 100, G, "Function a cut tendon or ligament takes from its part")
    motor_loss: int = rule(90, 0, 100, G, "Function a struck motor nerve takes from its part: a limp limb without severance")
    numbness_pct: int = rule(30, 0, 100, G, "Fine work a struck sensory nerve takes away: numbness")
    major_bleed: int = rule(30, 0, 100, G, "Blood lost each sampled stretch from a cut major artery (neck, trunk, thigh, upper arm)")
    minor_bleed: int = rule(10, 0, 100, G, "Blood lost each sampled stretch from a cut lesser artery")
    bleed_severity_pct: int = rule(25, 0, 100, G, "Extra bleeding per severity step above the first (%)")
    bleed_death_at: int = rule(20, 0, 100, G, "Blood below which the wounded bleed out and die")
    blood_regen: int = rule(15, 0, 100, G, "Blood a body makes back each epoch once no wound bleeds")
    bind_healer_pct: int = rule(85, 0, 100, G, "Chance a healer at hand binds a bleeding wound (%)")
    bind_first_aid_pct: int = rule(40, 0, 100, G, "Chance the wounded or a companion binds a bleeding wound with first aid at full medicine skill (%)")
    pain_will_pct: int = rule(60, 0, 100, G, "Pain a strong will masks at full will (%)")
    nausea_at: int = rule(30, 0, 100, G, "Felt pain at which the wounded grow nauseous")
    dizzy_at: int = rule(50, 0, 100, G, "Felt pain at which the wounded grow dizzy")
    unconscious_at: int = rule(75, 0, 100, G, "Felt pain at which the wounded fall unconscious")
    blood_faint_at: int = rule(45, 0, 100, G, "Blood below which the wounded fall unconscious from blood loss")
    nauseous_pct: int = rule(85, 0, 100, G, "Fighting and command left to the nauseous (%)")
    dizzy_pct: int = rule(60, 0, 100, G, "Fighting and command left to the dizzy (%)")
    unconscious_capture_pct: int = rule(60, 0, 100, G, "Chance an unconscious fighter on the losing side is taken captive (%)")
    exertion_per_fight: int = rule(25, 0, 100, G, "Exertion a fight costs a fighter in light gear")
    armour_exertion_pct: int = rule(40, 0, 200, G, "Extra exertion per point of armour density worn (% per 100)")
    exhausted_at: int = rule(70, 0, 100, G, "Exertion at which a fighter is exhausted")
    exhausted_pct: int = rule(70, 0, 100, G, "Fighting left to the exhausted (%)")
    exertion_recovery: int = rule(50, 0, 100, G, "Exertion a body sheds each epoch")
    duel_density_burden: int = rule(4, 0, 50, G, "Stamina each duel exchange costs per 100 points of worn armour density")
    unit_density_fatigue_pct: int = rule(30, 0, 200, G, "Extra fatigue a unit takes per point of its armour's density in a battle (% per 100)")
    diagnose_pct: int = rule(60, 0, 100, G, "Chance a healer of full medicine skill reads a wound right; a misread wastes the treatment (%)")
    diagnose_floor_pct: int = rule(30, 0, 100, G, "Chance even an unskilled healer reads a wound right (%)")
    clean_infection_pct: int = rule(50, 0, 100, G, "Infection a cleaned wound is spared (%)")
    set_bone_loss_pct: int = rule(50, 0, 100, G, "Lasting loss a set and splinted bone is spared (%)")
    amputate_at_years: int = span(1, 0, 500, G, "Years of infection after which a healer takes the festering limb to save the life")
    crutch_restore_pct: int = rule(40, 0, 100, G, "Walking a crutch gives back while a leg heals (%)")
    traction_restore_pct: int = rule(25, 0, 100, G, "Walking traction gives back to a broken leg while it heals (%)")
    suture_level: int = rule(1, 0, 20, G, "Medicine level needed to suture")
    set_bone_level: int = rule(2, 0, 20, G, "Medicine level needed to set a bone and splint it")
    amputate_level: int = rule(2, 0, 20, G, "Medicine level needed to amputate")
    cauterise_level: int = rule(1, 0, 20, G, "Medicine level needed to cauterise")
    traction_level: int = rule(3, 0, 20, G, "Medicine level needed for traction")

    @property
    def amputate_at(self) -> int:
        return self.epochs(self.amputate_at_years)
