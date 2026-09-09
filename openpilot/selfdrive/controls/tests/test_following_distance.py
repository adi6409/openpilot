import itertools
from openpilot.common.test import OpenpilotTestCase
from openpilot.common.parameterized import parameterized_class

from openpilot.cereal import log

from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_lead_danger_factor, get_obstacle_offset, get_safe_obstacle_distance
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_stopped_equivalence_factor
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_stop_distance, get_T_FOLLOW
from openpilot.selfdrive.controls.lib.longitudinal_planner import get_max_accel
from openpilot.selfdrive.test.longitudinal_maneuvers.maneuver import Maneuver


def desired_follow_distance(v_ego, v_lead, t_follow=None, stop_distance=None):
  if t_follow is None:
    t_follow = get_T_FOLLOW()
  stop_distance = get_stop_distance() if stop_distance is None else stop_distance
  return get_safe_obstacle_distance(v_ego, t_follow, stop_distance) - get_stopped_equivalence_factor(v_lead)

def run_following_distance_simulation(v_lead, t_end=100.0, e2e=False, personality=0):
  man = Maneuver(
    '',
    duration=t_end,
    initial_speed=float(v_lead),
    lead_relevancy=True,
    initial_distance_lead=100,
    speed_lead_values=[v_lead],
    breakpoints=[0.],
    e2e=e2e,
    personality=personality,
  )
  valid, output = man.evaluate()
  assert valid
  return output[-1,2] - output[-1,1]


class TestKaparaProfile(OpenpilotTestCase):
  def test_targets_are_closer_than_aggressive(self):
    self.assertLess(get_T_FOLLOW(log.LongitudinalPersonality.kapara), get_T_FOLLOW(log.LongitudinalPersonality.aggressive))
    self.assertLess(get_stop_distance(log.LongitudinalPersonality.kapara), get_stop_distance(log.LongitudinalPersonality.aggressive))
    self.assertEqual(get_stop_distance(log.LongitudinalPersonality.kapara), 1.0)

  def test_low_speed_acceleration_is_higher_than_aggressive(self):
    kapara_accel = get_max_accel(0.0, log.LongitudinalPersonality.kapara)
    aggressive_accel = get_max_accel(0.0, log.LongitudinalPersonality.aggressive)
    self.assertGreater(kapara_accel, aggressive_accel)

  def test_obstacle_offset_produces_kapara_stop_distance(self):
    physical_lead_distance = get_stop_distance(log.LongitudinalPersonality.kapara)
    obstacle_offset = get_obstacle_offset(log.LongitudinalPersonality.kapara)
    self.assertEqual(physical_lead_distance + obstacle_offset, get_stop_distance())

  def test_standstill_danger_zone_stays_proportional(self):
    personality = log.LongitudinalPersonality.kapara
    danger_distance = get_lead_danger_factor(personality) * get_stop_distance() - get_obstacle_offset(personality)
    self.assertEqual(danger_distance, 0.75 * get_stop_distance(personality))


@parameterized_class(("e2e", "personality", "speed"), itertools.product(
                      [True, False], # e2e
                      [log.LongitudinalPersonality.relaxed, # personality
                       log.LongitudinalPersonality.standard,
                       log.LongitudinalPersonality.aggressive,
                       log.LongitudinalPersonality.kapara],
                      [0,10,35])) # speed
class TestFollowingDistance(OpenpilotTestCase):
  def test_following_distance(self):
    v_lead = float(self.speed)
    simulation_steady_state = run_following_distance_simulation(v_lead, e2e=self.e2e, personality=self.personality)
    correct_steady_state = desired_follow_distance(v_lead, v_lead, get_T_FOLLOW(self.personality), get_stop_distance(self.personality))
    err_ratio = 0.2 if self.e2e else 0.1
    abs_err_margin = 0.5 if v_lead > 0.0 else 1.15
    self.assertAlmostEqual(simulation_steady_state, correct_steady_state,
                           delta=err_ratio * correct_steady_state + abs_err_margin)
