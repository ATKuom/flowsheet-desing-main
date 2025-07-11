import os
import numpy as np
import time
from scoSimulation import *
import copy


class Flowsheet:
    def __init__(self, sim, pure, max_iter, inlet_specs, Pressures):

        # Establish connection with ASPEN
        self.sim = sim

        # Characteristics of the environment
        self.d_actions = 10
        self.pure = pure
        self.max_iter = max_iter
        self.iter = 0
        self.actions_list = []
        self.co2 = 0.0
        self.Pressures = Pressures
        self.value_step = "pre"

        # Declare the initial flowrate conditions
        self.inlet_specs = inlet_specs

        # Flowsheet
        self.info = {}
        self.avail_actions = np.array(
            [
                1,  # Turbine
                1,  # Cooler
                1,  # Compressor
                1,  # Heater
                1,  # Heat exchanger
                1,  # Mixer
                0,  # EMPTY
                1,  # splitter
            ],
            dtype=np.int32,
        )

        self.turbine_count = 0
        self.cooler_count = 0
        self.compressor_count = 0
        self.heater_count = 0
        self.hex_count = 0
        self.mixer_count = 0
        self.splitter_count = 0

        self.reset()

    def get_outputs(self, sout):
        T = sout.get_temp()
        P = sout.get_press()
        Fco2 = sout.get_molar_flow("CO2")
        out_list = [T, P, Fco2]

        return out_list

    def step(self, action, sin):

        d_action = action[0]
        c_action = action[1]

        # ----------------------------------------- Turbine -----------------------------------------
        if d_action == 1:
            self.turbine_count += 1
            P_tur = c_action
            self.actions_list.append(f"T{self.turbine_count}")

            tur = Turbine(f"T{self.turbine_count}", P_tur, sin)
            sout = tur.expand()
            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"T{self.turbine_count}"] = [P_tur, self.get_outputs(sout)]

        # ----------------------------------------- Cooler -----------------------------------------
        elif d_action == 2:
            self.cooler_count += 1
            T_cooler = c_action
            P_cooler = self.Pressures[self.iter]
            self.actions_list.append(f"C{self.cooler_count}")

            cool = Cooler(f"C{self.cooler_count}", T_cooler, P_cooler, sin)

            sout = cool.cool()
            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"C{self.cooler_count}"] = [T_cooler, self.get_outputs(sout)]

        # ----------------------------------------- Compressor -----------------------------------------
        elif d_action == 3:
            self.compressor_count += 1
            P_comp = c_action
            self.actions_list.append(f"C{self.compressor_count}")

            comp = Compressor(f"C{self.compressor_count}", P_comp, sin)
            sout = comp.compress()
            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"C{self.compressor_count}"] = [
            #         P_comp,
            #         self.get_outputs(sout),
            #     ]

        # ----------------------------------------- Heater -----------------------------------------
        elif d_action == 4:
            self.heater_count += 1
            self.actions_list.append(f"H{self.heater_count}")
            T_heater = c_action
            P_heater = self.Pressures[self.iter]
            heater = Heater(f"H{self.heater_count}", T_heater, P_heater, sin)
            sout = heater.heat()
            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"H{self.heater_count}"] = [T_heater, self.get_outputs(sout)]

        # ----------------------------------------- Heat Exchanger -----------------------------------------
        elif d_action == 5:
            self.hex_count += 1
            self.actions_list.append(f"HX{self.hex_count}")
            DT_hex = c_action
            hex = HeatExchanger(f"HX{self.hex_count}", DT_hex, sin, self.hex_count)
            sout = hex.heat()
            if self.hex_count == 2:
                pass
                # self.sim.EngineRun()

                # if self.sim.Convergence():
                #     self.info[f"HX{self.hex_count}"] = [DT_hex, self.get_outputs(sout)]

        # ----------------------------------------- Mixer -----------------------------------------
        elif d_action == 7:
            self.mixer_count += 1
            self.actions_list.append(f"M{self.mixer_count}")

            mixer = Mixer(f"M{self.mixer_count}", sin, self.mixer_count)
            sout = mixer.mix()
            if self.mixer_count == 1:
                sout = self.splitter2ndstream
            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"M{self.mixer_count}"] = self.get_outputs(sout)
        # ----------------------------------------- Splitter -----------------------------------------
        elif d_action == 9:
            self.splitter_count += 1
            self.actions_list.append(f"S{self.splitter_count}")
            sr = c_action
            splitter = Splitter(f"S{self.splitter_count}", sr, sin)
            sout, self.splitter2ndstream = splitter.split()

            # self.sim.EngineRun()

            # if self.sim.Convergence():
            #     self.info[f"S{self.splitter_count}"] = self.get_outputs(sout)
        # ---------------------------------- Constraints and rewards ----------------------------------
        # if self.sim.Convergence():

        #     # Constraints

        #     # Cons 1: (Temperature inside of reactor no greater than 400°C)
        #     # if d_action in (4, 5) and sout.get_temp() <= 400:
        #     #     bonus_T = 0.4
        #     # else:
        #     #     bonus_T = 0.0

        #     # # Driving force (reduction of the amount of MeOH)
        #     # m_frac_prev = sin.get_molar_flow("METHANOL") / sin.get_total_molar_flow()
        #     # m_frac = sout.get_molar_flow("METHANOL") / sout.get_total_molar_flow()
        #     # bonus = m_frac_prev - m_frac

        #     # # Cons 2. Output purities
        #     # if not self.water_pure:
        #     #     w_frac = sout.get_molar_flow("WATER") / sout.get_total_molar_flow()
        #     #     self.water_pure = w_frac >= self.pure

        #     # if self.dme_out != 0:
        #     #     self.dme_pure = (
        #     #         self.dme_out.get_molar_flow("DME")
        #     #         / self.dme_out.get_total_molar_flow()
        #     #         >= self.pure
        #     #     )

        #     # penalty = 0
        #     # reward_flow = 0
        #     # dme_extra = 0

        #     # if self.iter >= self.max_iter:
        #     #     self.done = True

        #     #     if not self.water_pure or not self.dme_pure:
        #     #         penalty -= 15 * (self.pure - w_frac)
        #     # else:
        #     #     if self.water_pure and self.dme_pure:
        #     #         self.done = True
        #     #         reward_flow += 0.2 * (self.max_iter - self.iter)

        #     # if self.water_pure and not self.dme_pure:
        #     #     sout = self.dme_out

        #     # # Reward for more DME flow
        #     # if self.dme_pure and not self.dme_extra_added:
        #     #     dme_extra = self.dme_out.get_molar_flow("DME") / (self.Cao / 2)
        #     #     self.dme_extra_added = True  # Set the flag to True to indicate that dme_extra has been added

        #     # reward = cost + bonus + bonus_T + penalty + reward_flow + dme_extra
        #     reward = 0
        #     self.state = np.array(
        #         [
        #             sout.get_temp(),
        #             sout.get_press(),
        #             sout.get_mass_flow(),
        #             self.iter / self.max_iter,
        #         ]
        #     )

        # else:
        #     self.done = True
        #     reward = -8

        # Return step information
        self.iter += 1
        return self.state, self.done, self.info, sout

    def fixed_cost_reactor(self, D, H):
        M_S = 1638.2  # Marshall & Swift equipment index 2018 (1638.2, fixed)
        f_cost = (M_S) / 280 * 101.9 * D**1.066 * H**0.802 * (2.18 + 1.15)
        max_cost = (M_S) / 280 * 101.9 * 3.5**1.066 * 12**0.802 * (2.18 + 1.15)
        norm_cost = f_cost / max_cost
        return norm_cost

    def fixed_cost_column(self, D, H):
        M_S = 1638.2  # Marshall & Swift equipment index 2018 (1638.2, fixed)
        max_H = 1.2 * 0.61 * (25 - 2)
        # Internal costs
        int_cost = (M_S) / 280 * D**1.55 * H
        max_int_cost = (M_S) / 280 * 2.5**1.55 * max_H
        norm_cost1 = int_cost / max_int_cost

        # External costs
        f_cost = (M_S) / 280 * 101.9 * D**1.066 * H**0.802 * (2.18 + 1.15)
        max_cost = (M_S) / 280 * 101.9 * 2.5**1.066 * max_H**0.802 * (2.18 + 1.15)
        norm_cost2 = f_cost / max_cost

        return norm_cost1 + norm_cost2

    def action_masks(self, sin, inlet=None):
        self.masking(sin, inlet)
        v1 = np.ones((self.d_actions,), dtype=np.int32) * self.avail_actions
        mask_vec = np.where(v1 > 0, 1, 0)
        mask_vec = np.array(mask_vec, dtype=bool)
        return mask_vec

    def render(self):
        for i in self.info:
            print(f"{i}: {self.info[i]}")

    def interpolation(self, c_action):
        (
            T_hex,
            T_cooler,
            D1,
            L1,
            D2,
            L2,
            nstages_c,
            dist_rate_c,
            mid_rate_c,
            nstages_cr,
            mid_rate_cr,
            rr_cr,
            nstages_tc,
            dist_rate_tc,
            mid_rate_tc,
            nstages_tcr,
            dist_rate_tcr,
            mid_rate_tcr,
            rr_tcr,
        ) = c_action

        T_hex = np.interp(T_hex, [0, 1], (150, 400))
        T_cooler = np.interp(T_cooler, [0, 1], (5, 50))
        D1 = np.interp(D1, [0, 1], (0.5, 3.5))
        L1 = np.interp(L1, [0, 1], (6.5, 12.0))
        D2 = np.interp(D2, [0, 1], (0.5, 3.5))
        L2 = np.interp(L2, [0, 1], (6.5, 12.0))
        nstages_c = round(np.interp(nstages_c, [0, 1], [5, 25]) + 0.5)
        dist_rate_c = np.interp(dist_rate_c, [0, 1], (70.0, 110.0))
        mid_rate_c = np.interp(mid_rate_c, [0, 1], (20.0, 60.0))
        nstages_cr = round(np.interp(nstages_cr, [0, 1], [5, 25]) + 0.5)
        mid_rate_cr = np.interp(mid_rate_cr, [0, 1], (20.0, 60.0))
        rr_cr = np.interp(rr_cr, [0, 1], (0.5, 0.95))
        nstages_tc = round(np.interp(nstages_tc, [0, 1], [5, 25]) + 0.5)
        dist_rate_tc = np.interp(dist_rate_tc, [0, 1], (70.0, 110.0))
        mid_rate_tc = np.interp(mid_rate_tc, [0, 1], (20.0, 60.0))
        nstages_tcr = round(np.interp(nstages_tcr, [0, 1], [5, 25]) + 0.5)
        dist_rate_tcr = np.interp(dist_rate_tcr, [0, 1], (70.0, 110.0))
        mid_rate_tcr = np.interp(mid_rate_tcr, [0, 1], (20.0, 60.0))
        rr_tcr = np.interp(rr_tcr, [0, 1], (0.5, 0.95))

        y = (
            T_hex,
            T_cooler,
            D1,
            L1,
            D2,
            L2,
            nstages_c,
            dist_rate_c,
            mid_rate_c,
            nstages_cr,
            mid_rate_cr,
            rr_cr,
            nstages_tc,
            dist_rate_tc,
            mid_rate_tc,
            nstages_tcr,
            dist_rate_tcr,
            mid_rate_tcr,
            rr_tcr,
        )

        return y

    def reset(self):
        # Reset all instances
        self.iter = 0
        self.sim.Reinitialize()
        # inlet_specs is going to be a list of lists which contains variables and dictionaries for compounds
        self.state = np.zeros(
            (len(self.inlet_specs), len(self.inlet_specs[0])), dtype=np.float32
        )
        sin = [None] * len(self.inlet_specs)
        for i in range(len(self.inlet_specs)):
            T, P, compounds = self.inlet_specs[i]
            Fco2 = compounds["CO2"]
            sin[i] = Stream(f"IN{i+1}", self.inlet_specs[i])

            self.state[i] = np.array([T, P, Fco2])

        self.info.clear()
        self.actions_list.clear()
        self.done = False
        self.avail_actions = np.array([1, 1, 1, 1, 1, 1], dtype=np.int32)

        self.mixer_count = 0
        self.hex_count = 0
        self.cooler_count = 0
        self.pump_count = 0
        self.reac_count = 0
        self.column_count = 0

        return self.state, sin

    def masking(self, sin, inlet):

        if inlet:
            T, P, _ = self.inlet_specs
            meoh_flow = self.Cao
            conv = 0

        else:
            T = sin.get_temp()
            P = sin.get_press()
            meoh_flow = sin.get_molar_flow("METHANOL")
            conv = (self.Cao - meoh_flow) / self.Cao

        if self.water_pure:
            self.value_step = "pure"
        # Preprocess
        elif T >= 200 and P >= 1 and conv < 0.1:
            self.value_step = "reac"
        elif conv >= 0.75 and self.value_step == "reac":
            self.value_step = "cool"
        elif self.value_step == "cool" or self.value_step == "distill":
            self.value_step = "distill"

        # Preparation step
        if self.value_step == "pre":
            # Pump deactivation and heater activation (otherwise error in simulation)
            if P > 1:
                self.avail_actions[2] = 0
                self.avail_actions[1] = 1

        elif self.value_step == "reac":
            self.avail_actions = np.array(
                [0, 0, 0, 0, 1, 1, 0, 0, 0, 0], dtype=np.int32
            )

        elif self.value_step == "cool":
            self.avail_actions = np.array(
                [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], dtype=np.int32
            )

        elif self.value_step == "distill":
            self.avail_actions = np.array(
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0], dtype=np.int32
            )

            if any("M" in action for action in self.actions_list):
                if any("DC" in action for action in self.actions_list):
                    self.avail_actions[6] = 0
                    self.avail_actions[7] = 1
                else:
                    self.avail_actions[9] = 1
            else:
                self.avail_actions[8] = 1

        elif self.value_step == "pure":
            self.avail_actions = np.array(
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0], dtype=np.int32
            )

        return self.avail_actions
