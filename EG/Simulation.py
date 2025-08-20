import os
import win32com.client as win32
import numpy as np


class Simulation:
    AspenSimulation = win32.gencache.EnsureDispatch("Apwn.Document")

    def __init__(self, AspenFileName, WorkingDirectoryPath, VISIBILITY=False):
        os.chdir(WorkingDirectoryPath)
        print(f"Working Directory: {os.getcwd()}")
        print(f"Aspen File: {AspenFileName}")
        self.AspenSimulation.InitFromArchive2(os.path.abspath(AspenFileName))
        self.AspenSimulation.Visible = VISIBILITY
        self.AspenSimulation.SuppressDialogs = True

    def CloseAspen(self):
        AspenFileName = self.Give_AspenDocumentName()
        self.AspenSimulation.Close(os.path.abspath(AspenFileName))

    def Quit(self):
        self.AspenSimulation.Quit()

    def Give_AspenDocumentName(self):
        return self.AspenSimulation.FullName

    @property
    def BLK(self):
        return self.AspenSimulation.Tree.Elements("Data").Elements("Blocks")

    @property
    def STRM(self):
        return self.AspenSimulation.Tree.Elements("Data").Elements("Streams")

    def EngineRun(self):
        self.AspenSimulation.Run2()

    def EngineStop(self):
        self.AspenSimulation.Stop()

    def EngineReinit(self):
        self.AspenSimulation.Reinit()

    def Convergence(self):
        converged = (
            self.AspenSimulation.Tree.Elements("Data")
            .Elements("Results Summary")
            .Elements("Run-Status")
            .Elements("Output")
            .Elements("PER_ERROR")
            .Value
        )
        return converged == 0

    def StreamConnect(self, Blockname, Streamname, Portname):
        self.BLK.Elements(Blockname).Elements("Ports").Elements(Portname).Elements.Add(
            Streamname
        )

    def StreamDisconnect(self, Blockname, Streamname, Portname):
        self.BLK.Elements(Blockname).Elements("Ports").Elements(
            Portname
        ).Elements.Remove(Streamname)

    def Reinitialize(self):
        self.STRM.RemoveAll()
        self.BLK.RemoveAll()
        self.AspenSimulation.Reinit()


class Stream(Simulation):
    def __init__(self, name, inlet=False):
        self.name = name.upper()
        self.inlet = inlet

        self.StreamPlace()

        if self.inlet:
            self.inlet_stream()

    def StreamPlace(self):
        compositstring = self.name + "!" + "MATERIAL"
        self.STRM.Elements.Add(compositstring)

    def StreamDelete(self):
        self.STRM.Elements.Remove(self.name)

    def inlet_stream(self):
        T = self.inlet[0]
        P = self.inlet[1]
        comp = self.inlet[2]

        self.STRM.Elements(self.name).Elements("Input").Elements("TEMP").Elements(
            "MIXED"
        ).Value = T
        self.STRM.Elements(self.name).Elements("Input").Elements("PRES").Elements(
            "MIXED"
        ).Value = P

        for chemical in comp:
            self.STRM.Elements(self.name).Elements("Input").Elements("FLOW").Elements(
                "MIXED"
            ).Elements(chemical).Value = comp[chemical]

    def set_temp(self, temp):
        self.STRM.Elements(self.name).Elements("Input").Elements("TEMP").Elements(
            "MIXED"
        ).Value = temp

    def set_press(self, press):
        self.STRM.Elements(self.name).Elements("Input").Elements("PRES").Elements(
            "MIXED"
        ).Value = press

    def set_mass_flow(self, comp):
        for chemical in comp:
            self.STRM.Elements(self.name).Elements("Input").Elements("FLOW").Elements(
                "MIXED"
            ).Elements(chemical).Value = comp[chemical]

    def get_temp(self):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("TEMP_OUT")
            .Elements("MIXED")
            .Value
        )

    def get_press(self):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("PRES_OUT")
            .Elements("MIXED")
            .Value
        )

    def get_molar_flow(self, compound):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("MOLEFLOW")
            .Elements("MIXED")
            .Elements(compound)
            .Value
        )

    def get_total_molar_flow(self):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("MOLEFLMX")
            .Elements("MIXED")
            .Value
        )

    def get_vapor_fraction(self):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("STR_MAIN")
            .Elements("VFRAC")
            .Elements("MIXED")
            .Value
        )

    def get_mass_flow(self):
        return (
            self.STRM.Elements(self.name)
            .Elements("Output")
            .Elements("MASSFLMX")
            .Elements("MIXED")
            .Value
        )

    def stream_specs(self):
        return (self.get_temp(), self.get_press(), self.get_mass_flow())


class Block(Simulation):
    def __init__(self, name, uo):
        self.name = name.upper()
        self.uo = uo

    def BlockCreate(self):
        compositestring = self.name + "!" + self.uo
        self.BLK.Elements.Add(compositestring)

    def BlockDelete(self):
        self.BLK.Elements.Remove(self.name)

    def capital_cost(self):
        # Placeholder for capital cost calculation
        return 0

    def operating_cost(self):
        # Placeholder for operating cost calculation
        return 0


# -------------------------------------------------- UNIT OPERATIONS ------------------------------------------------


class InitialMixer(Block):
    def __init__(self, name, inlet_streams):
        super().__init__(name, "Mixer")
        self.name = name
        self.inlet_streams = inlet_streams
        self.BlockCreate()
        self.BLK.Elements(self.name).Elements("Input").Elements("PRES").Value = 0

    def connect(self):
        # Inlet connection
        for stream in self.inlet_streams:
            self.StreamConnect(self.name, stream.name, "F(IN)")

        # self.BLK.Elements(self.name).Elements("Input").Elements("NPHASE").Value = 1
        # self.BLK.Elements(self.name).Elements("Input").Elements("PHASE").Value = "L"

        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, *args):
        # This method can be used to set any design variable for the mixer
        # Currently, no specific design variables are set for the mixer
        pass


class Mixer(Block):
    def __init__(self, name, inlet_streams):
        super().__init__(name, "Mixer")
        self.name = name
        self.inlet_streams = inlet_streams
        self.BlockCreate()
        self.BLK.Elements(self.name).Elements("Input").Elements("PRES").Value = 0

    def connect(self, stream):
        self.StreamConnect(self.name, stream.name, "F(IN)")
        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, *args):
        # This method can be used to set any design variable for the mixer
        # Currently, no specific design variables are set for the mixer
        pass


class Splitter(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "FSplit")

        self.name = name
        self.inlet_stream = inlet_stream
        self.sr = 0.5  # Default split ratio
        self.BlockCreate()

    def connect(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        self.s1 = Stream(f"{self.name}S1OUT")
        s2 = Stream(f"{self.name}S2OUT")

        self.StreamConnect(self.name, self.s1.name, "P(OUT)")
        self.StreamConnect(self.name, s2.name, "P(OUT)")

        return self.s1, s2

    def dv_placement(self, split_ratio):
        self.BLK.Elements(self.name).Elements("Input").Elements("FRAC").Elements(
            self.s1.name
        ).Value = split_ratio


class Heater(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "Heater")

        self.name = name
        self.inlet_stream = inlet_stream
        self.Temp = 298.15  # Default temperature in Kelvin
        self.BlockCreate()
        self.DT = 20

    def connect(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        self.BLK.Elements(self.name).Elements("Input").Elements(
            "SPEC_OPT"
        ).Value = "TDPPARM"
        self.BLK.Elements(self.name).Elements("Input").Elements("DPPARM").Value = "0"
        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, temp):
        self.BLK.Elements(self.name).Elements("Input").Elements("TEMP").Value = temp

    def energy_consumption(self):
        self.q = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("QCALC").Value
        )
        return self.q

    def capital_cost(self):
        U = 500  # W/m2.K
        self.area = self.q / (U * self.DT)
        M = 0.68
        Cb = 3.28e4
        Qb = 80  # m2
        cost = Cb * (self.area / Qb) ** M
        return cost

    def operating_cost(self):
        cost_of_mp = 0.00962 / 2160  # $/kj


class Cooler(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "Heater")

        self.name = name
        self.inlet_stream = inlet_stream
        self.Temp = 298.15
        self.BlockCreate()
        self.DT = 20

    def connect(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        self.BLK.Elements(self.name).Elements("Input").Elements(
            "SPEC_OPT"
        ).Value = "TDPPARM"
        self.BLK.Elements(self.name).Elements("Input").Elements("DPPARM").Value = "0"
        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, temp):
        self.BLK.Elements(self.name).Elements("Input").Elements("TEMP").Value = temp

    def energy_consumption(self):
        self.q = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("QCALC").Value
        )
        return self.q

    def capital_cost(self):
        U = 500  # W/m2.K
        self.area = self.q / (U * self.DT)
        M = 0.68
        Cb = 3.28e4
        Qb = 80  # m2
        cost = Cb * (self.area / Qb) ** M
        return cost


class HeatExchanger(Block):
    def __init__(self, name, inlet_stream1, inlet_stream2=None):
        super().__init__(name, "HeatX")
        self.name = name
        self.inlet_stream1 = inlet_stream1
        self.inlet_stream2 = inlet_stream2
        self.BlockCreate()
        # self.hotside_pres = pres
        # self.BLK.Elements(self.name).Elements("Input").Elements(
        # "PRES_HOT").Value = self.hotside_pres
        #             self.coldside_pres = pres
        # self.BLK.Elements(self.name).Elements("Input").Elements(
        # "PRES_COLD").Value = self.coldside_pres

    def connect(self, hex_count, sin2=None):
        if hex_count == 1:
            self.StreamConnect(self.name, self.inlet_stream1.name, "H(IN)")
            s = Stream(f"{self.name}OUT1")
            self.StreamConnect(self.name, s.name, "H(OUT)")
            self.BLK.Elements(self.name).Elements("Input").Elements(
                "SPEC"
            ).Value = "DELT-HOT"
            self.outlet1 = s
        else:
            self.inlet_stream2 = sin2
            self.StreamConnect(self.name, self.inlet_stream2.name, "C(IN)")
            s = Stream(f"{self.name}OUT2")
            self.StreamConnect(self.name, s.name, "C(OUT)")
            self.outlet2 = s
        return s

    def dv_placement(self, DT):
        self.DT = DT
        self.BLK.Elements(self.name).Elements("Input").Elements("VALUE").Value = self.DT

    def switch_streams(self):
        # Switch the inlet streams for the heat exchanger
        self.StreamDisconnect(self.name, self.inlet_stream1.name, "H(IN)")
        self.StreamDisconnect(self.name, self.inlet_stream2.name, "C(IN)")
        self.StreamConnect(self.name, self.inlet_stream2.name, "H(IN)")
        self.StreamConnect(self.name, self.inlet_stream1.name, "C(IN)")
        new_coldside_pres = self.hotside_pres
        new_hotside_pres = self.coldside_pres

        # Update the outlet streams accordingly
        self.StreamDisconnect(self.name, self.outlet1.name, "H(OUT)")
        self.StreamDisconnect(self.name, self.outlet2.name, "C(OUT)")
        self.StreamConnect(self.name, self.outlet2.name, "H(OUT)")
        self.StreamConnect(self.name, self.outlet1.name, "C(OUT)")
        self.hotside_pres = new_hotside_pres
        self.coldside_pres = new_coldside_pres
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES_HOT"
        ).Value = self.hotside_pres
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES_COLD"
        ).Value = self.coldside_pres

    def undo_switch(self):
        # Switch the inlet streams back to their original state
        self.StreamDisconnect(self.name, self.inlet_stream2.name, "H(IN)")
        self.StreamDisconnect(self.name, self.inlet_stream1.name, "C(IN)")
        self.StreamConnect(self.name, self.inlet_stream1.name, "H(IN)")
        self.StreamConnect(self.name, self.inlet_stream2.name, "C(IN)")
        new_coldside_pres = self.hotside_pres
        new_hotside_pres = self.coldside_pres

        # Update the outlet streams accordingly
        self.StreamDisconnect(self.outlet2.name, "H(OUT)")
        self.StreamDisconnect(self.outlet1.name, "C(OUT)")
        self.StreamConnect(self.outlet1.name, "H(OUT)")
        self.StreamConnect(self.outlet2.name, "C(OUT)")
        self.hotside_pres = new_hotside_pres
        self.coldside_pres = new_coldside_pres
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES_HOT"
        ).Value = self.hotside_pres
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES_COLD"
        ).Value = self.coldside_pres

    def energy_consumption(self):
        self.q = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("HX_DUTY").Value
        )
        return self.q

    def capital_cost(self):
        U = 500  # W/m2.K
        self.area = self.q / (U * self.DT)
        M = 0.68
        Cb = 3.28e4
        Qb = 80  # m2
        cost = Cb * (self.area / Qb) ** M
        return cost


class Pump(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "Pump")
        self.name = name
        self.press = 2.4  # Default pressure in bar
        self.inlet_stream = inlet_stream

        self.BlockCreate()

    def connect(self):
        # Inlet connection
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")
        self.BLK.Elements(self.name).Elements("Input").Elements("EFF").Value = 0.5
        self.BLK.Elements(self.name).Elements("Input").Elements("DEFF").Value = 0.9
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "OPT_SPEC"
        ).Value = "PRES"

        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, press):
        self.BLK.Elements(self.name).Elements("Input").Elements("PRES").Value = press

    def energy_consumption(self):
        self.q = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("WNET").Value
        )
        return self.q

    def capital_cost(self):
        M = 0.55
        Cb = 9.84e3
        Qb = 4  # kW
        cost = Cb * (self.q * 1000 / Qb) ** M
        return cost


class CSTR_A(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "RCSTR")
        self.name = name
        self.inlet_stream = inlet_stream
        self.volume = 30  # Default volume in m^3

        self.BlockCreate()

    def connect(self):
        # Inlet connection
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        # Reactors specifications
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "SPEC_OPT"
        ).Value = "DUTY"
        self.BLK.Elements(self.name).Elements("Input").Elements("DUTY").Value = 0
        self.BLK.Elements(self.name).Elements("Input").Elements("PHASE").Value = "L"

        # Reaction
        nodes = self.AspenSimulation.Application.Tree.FindNode(
            f"/Data/Blocks/{self.name}/Input/RXN_ID"
        ).Elements
        nodes.InsertRow(1, nodes.Count)
        nodes(nodes.Count - 1).Value = "EGR"
        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, volume):
        self.volume = volume
        self.BLK.Elements(self.name).Elements("Input").Elements("VOL").Value = volume

    def capital_cost(self):
        M = 0.45
        Cb = 1.15e4
        Qb = 1
        cost = Cb * (self.volume / Qb) ** M
        return cost


class PFR_A(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "RPlug")
        self.name = name
        self.inlet_stream = inlet_stream
        self.volume = 30  # Default volume in m^3

        self.BlockCreate()

    def connect(self):
        # Inlet connection
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        # Reactors specifications
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "TYPE"
        ).Value = "ADIABATIC"

        # Sizing
        self.BLK.Elements(self.name).Elements("Input").Elements("NPHASE").Value = 1
        self.BLK.Elements(self.name).Elements("Input").Elements("PHASE").Value = "L"

        # Reaction
        nodes = self.AspenSimulation.Application.Tree.FindNode(
            f"/Data/Blocks/{self.name}/Input/RXN_ID"
        ).Elements
        nodes.InsertRow(1, nodes.Count)
        nodes(nodes.Count - 1).Value = "EGR"

        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, volume):
        self.volume = volume
        self.D = (4 * volume / (np.pi * 6)) ** (1 / 3)
        self.L = 6 * self.D
        self.BLK.Elements(self.name).Elements("Input").Elements("LENGTH").Value = self.L
        self.BLK.Elements(self.name).Elements("Input").Elements("DIAM").Value = self.D

    def capital_cost(self):
        M = 0.82
        Cb = 9.84e4
        Qb = 6
        P = 20e5  # AveragePressure
        S = 120e6  # allowable stress
        E = 0.0015  # corrosion allowance
        rho = 7850  # carbon steel
        t_req = (P * self.D) / (2 * S * E - 0.6 * P)
        D_o = self.D + 2 * t_req
        V_shell = np.pi * self.L * ((D_o / 2) ** 2 - (self.D / 2) ** 2)
        Q = rho * V_shell / 1000
        cost = Cb * (Q / Qb) ** M
        return cost


class Column(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "Radfrac")
        self.name = name
        self.nstages = 12  # Default number of stages
        self.reflux_ratio = 0.024
        self.bottoms_flow = 26.3
        self.press = 2.4  # Default pressure in bar
        self.inlet_stream = inlet_stream

        self.BlockCreate()

    def connect(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        # Configuration
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CALC_MODE"
        ).Value = "EQUILIBRIUM"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "NSTAGE"
        ).Value = self.nstages
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CONDENSER"
        ).Value = "TOTAL"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "REBOILER"
        ).Value = "KETTLE"
        self.BLK.Elements(self.name).Elements("Input").Elements("NO_PHASE").Value = 2
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CONV_METH"
        ).Value = "STANDARD"

        # Convergence
        self.BLK.Elements(self.name).Elements("Input").Elements("MAXOL").Value = 200

        d = Stream(f"{self.name}DOUT")
        self.StreamConnect(self.name, d.name, "LD(OUT)")
        b = Stream(f"{self.name}BOUT")
        self.StreamConnect(self.name, b.name, "B(OUT)")
        return d, b

    def dv_placement(self, pressure):
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES1"
        ).Value = pressure

    def set_ops(self, stages, reflux_ratio, bottoms_ratio):
        self.nstages = stages
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "NSTAGE"
        ).Value = self.nstages
        self.BLK.Elements(self.name).Elements("Input").Elements("FEED_STAGE").Elements(
            self.inlet_stream.name
        ).Value = round(self.nstages / 2, 0)
        self.BLK.Elements(self.name).Elements("Input").Elements("FEED_CONVE2").Elements(
            self.inlet_stream.name
        ).Value = "ABOVE-STAGE"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "BASIS_RR"
        ).Value = reflux_ratio
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "B:F"
        ).Value = bottoms_ratio

    def energy_consumption(self):
        q1 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("COND_DUTY").Value
        )
        q2 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("REB_DUTY").Value
        )
        return q1 + q2

    def capital_cost(self):
        Mtray = 0.91
        Cbtray = 6.56e3
        Qbtray = 0.5
        Qtray = 4
        M = 0.89
        Cb = 6.56e4
        Qb = 8
        L = 0.6 * self.nstages + 2
        D = 0.4
        S = 120e6  # allowable stress
        E = 0.0015  # corrosion allowance
        rho = 7850  # carbon steel
        t_req = (self.press * D) / (2 * S * E - 0.6 * self.press)
        D_o = D + 2 * t_req
        V_shell = np.pi * L * ((D_o / 2) ** 2 - (D / 2) ** 2)
        Q = rho * V_shell / 1000
        column_cost = Cb * (Q / Qb) ** M
        tray_cost = self.nstages / 10 * (Cbtray * (Qtray / Qbtray) ** Mtray)
        return column_cost + tray_cost


class SColumn(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "Distl")
        self.name = name
        self.inlet_stream = inlet_stream

        self.BlockCreate()

    def connect(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        d = Stream(f"{self.name}DOUT")
        self.StreamConnect(self.name, d.name, "D(OUT)")
        b = Stream(f"{self.name}BOUT")
        self.StreamConnect(self.name, b.name, "B(OUT)")
        return d, b

    def dv_placement(self, pressure):
        self.BLK.Elements(self.name).Elements("Input").Elements("PTOP").Value = pressure
        self.BLK.Elements(self.name).Elements("Input").Elements("PBOT").Value = pressure

    def set_ops(self, nstages, rr, df):
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "NSTAGE"
        ).Value = nstages
        self.BLK.Elements(self.name).Elements("Input").Elements("FEED_LOC").Value = (
            round(nstages / 2)
        )
        self.BLK.Elements(self.name).Elements("Input").Elements("RR").Value = rr
        self.BLK.Elements(self.name).Elements("Input").Elements("D_F").Value = df

    def energy_consumption(self):
        q1 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("COND_DUTY").Value
        )
        q2 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("REB_DUTY").Value
        )
        return q1 + q2


class Compressor(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "COMPR")
        self.name = name
        self.inlet_stream = inlet_stream
        self.press = 2.4  # Default pressure in bar

        self.BlockCreate()

    def connect(self):
        # Inlet connection
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "MODEL_TYPE"
        ).Value = "COMPRESSOR"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "TYPE"
        ).Value = "ISENTROPIC"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "OPT_SPEC"
        ).Value = "PRES"
        self.BLK.Elements(self.name).Elements("Input").Elements("NPHASE").Value = 2
        self.BLK.Elements(self.name).Elements("Input").Elements("SEFF").Value = 0.82

        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def energy_consumption(self):
        q = abs(self.BLK.Elements(self.name).Elements("Output").Elements("WNET").Value)
        return q

    def dv_placement(self, press):
        self.BLK.Elements(self.name).Elements("Input").Elements("PRES").Value = press


class Turbine(Block):
    def __init__(self, name, inlet_stream):
        super().__init__(name, "COMPR")
        self.name = name
        self.inlet_stream = inlet_stream
        self.press = 2.4  # Default pressure in bar

        self.BlockCreate()

    def connect(self):
        # Inlet connection
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "MODEL_TYPE"
        ).Value = "TURBINE"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "TYPE"
        ).Value = "ISENTROPIC"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "OPT_SPEC"
        ).Value = "PRES"
        self.BLK.Elements(self.name).Elements("Input").Elements("NPHASE").Value = 2
        self.BLK.Elements(self.name).Elements("Input").Elements("SEFF").Value = 0.85

        s = Stream(f"{self.name}OUT")
        self.StreamConnect(self.name, s.name, "P(OUT)")
        return s

    def dv_placement(self, press):
        self.BLK.Elements(self.name).Elements("Input").Elements("PRES").Value = press

    def energy_consumption(self):
        q = abs(self.BLK.Elements(self.name).Elements("Output").Elements("WNET").Value)
        return q


class TriColumn(Block):
    def __init__(
        self, name, nstages, dist_rate, reflux_ratio, press, mid_rate, inlet_stream
    ):
        super().__init__(name, "Radfrac")
        self.name = name
        self.nstages = nstages
        self.dist_rate = dist_rate
        self.reflux_ratio = reflux_ratio
        self.press = press
        self.mid_rate = mid_rate
        self.inlet_stream = inlet_stream

        self.BlockCreate()

    def distill(self):
        self.StreamConnect(self.name, self.inlet_stream.name, "F(IN)")

        # Configuration
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CALC_MODE"
        ).Value = "EQUILIBRIUM"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "NSTAGE"
        ).Value = self.nstages
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CONDENSER"
        ).Value = "TOTAL"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "REBOILER"
        ).Value = "KETTLE"
        self.BLK.Elements(self.name).Elements("Input").Elements("NO_PHASE").Value = 2
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "CONV_METH"
        ).Value = "STANDARD"
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "BASIS_D"
        ).Value = self.dist_rate
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "BASIS_RR"
        ).Value = self.reflux_ratio

        # Streams
        self.BLK.Elements(self.name).Elements("Input").Elements("FEED_STAGE").Elements(
            self.inlet_stream.name
        ).Value = round(self.nstages / 3, 0)
        self.BLK.Elements(self.name).Elements("Input").Elements("FEED_CONVE2").Elements(
            self.inlet_stream.name
        ).Value = "ABOVE-STAGE"

        # Pressure
        self.BLK.Elements(self.name).Elements("Input").Elements(
            "PRES1"
        ).Value = self.press

        # Convergence
        self.BLK.Elements(self.name).Elements("Input").Elements("MAXOL").Value = 200

        # Tray sizing
        self.BLK.Elements(self.name).Elements("Subobjects").Elements(
            "Tray Sizing"
        ).Elements.Add("1")

        self.BLK.Elements(self.name).Elements("Subobjects").Elements(
            "Tray Sizing"
        ).Elements("1").Elements("Input").Elements("TS_STAGE1").Elements("1").Value = 2
        self.BLK.Elements(self.name).Elements("Subobjects").Elements(
            "Tray Sizing"
        ).Elements("1").Elements("Input").Elements("TS_STAGE2").Elements("1").Value = (
            self.nstages - 1
        )
        self.BLK.Elements(self.name).Elements("Subobjects").Elements(
            "Tray Sizing"
        ).Elements("1").Elements("Input").Elements("TS_TRAYTYPE").Elements(
            "1"
        ).Value = "SIEVE"

        d = Stream(f"{self.name}DOUT")
        self.StreamConnect(self.name, d.name, "LD(OUT)")
        mid = Stream(f"{self.name}MOUT")
        self.StreamConnect(self.name, mid.name, "SP(OUT)")
        b = Stream(f"{self.name}BOUT")
        self.StreamConnect(self.name, b.name, "B(OUT)")

        self.BLK.Elements(self.name).Elements("Input").Elements("PROD_PHASE").Elements(
            mid.name
        ).Value = "L"
        self.BLK.Elements(self.name).Elements("Input").Elements("PROD_STAGE").Elements(
            mid.name
        ).Value = round(self.nstages / 2, 0)
        self.BLK.Elements(self.name).Elements("Input").Elements("PROD_FLOW").Elements(
            mid.name
        ).Value = self.mid_rate

        return d, mid, b

    def energy_consumption(self):
        q1 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("COND_DUTY").Value
        )
        q2 = abs(
            self.BLK.Elements(self.name).Elements("Output").Elements("REB_DUTY").Value
        )
        return q1 + q2

    def sizing(self):
        D = (
            self.BLK.Elements(self.name)
            .Elements("Subobjects")
            .Elements("Tray Sizing")
            .Elements("1")
            .Elements("Output")
            .Elements("DIAM4")
            .Elements("1")
            .Value
        )
        H = 1.2 * 0.61 * (self.nstages - 2)

        return D, H


class Empty_block(Block):
    def __init__(self, name):
        super().__init__(name, "Empty")
        self.name = name

    def dv_placement(self, *args):
        pass
