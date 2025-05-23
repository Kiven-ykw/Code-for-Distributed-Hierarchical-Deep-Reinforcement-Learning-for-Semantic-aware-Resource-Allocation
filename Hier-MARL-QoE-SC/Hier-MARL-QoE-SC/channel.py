""" simulator for channels"""

from config import Config
import functions as f
import numpy as np
import pandas as pd


df = pd.read_csv('DeepSC_table.csv')
DeepSC_table = df.values

class Channel:

    def __init__(self, bs, ue):
        """ establish a channel given a BS and a UE """

        self.bs = bs
        self.ue = ue
        self.index = np.array([bs.index, ue.index])

        self.beta = None
        self.phi_req = None
        self.phi = None
        self.lambda_ = None
        self.xi_req = None
        self.w = np.array(180e3, dtype=np.float32)

        self.norminal_aod = f.get_azimuth(bs.location, ue.location)
        self.angular_spread = Config().angular_spread
        self.multi_paths = Config().multi_paths
        self.rho = Config().rho

        self.d = np.linalg.norm(self.bs.location - self.ue.location)
        self.path_loss = 1 / f.dB2num(120.9 + 37.6 * np.log10(self.d / 1000) + np.random.normal(0, 8))
        self._check_is_link_()
        self._generate_steering_vector_()
        self.g = (np.random.randn(1, self.multi_paths) + np.random.randn(1, self.multi_paths) * 1j) / np.sqrt(2 * self.multi_paths)
        self._cal_csi_(ir_change=True)
        # for saving outdated csi
        self.h1, self.h2 = None, None
        self.r_power10, self.r_power11, self.r_power20, self.r_power21 = None, None, None, None
        self.gain10, self.gain11, self.gain20, self.gain21 = None, None, None, None

    def _generate_steering_vector_(self):

        self.aod = self.norminal_aod + (np.random.rand(self.multi_paths) - 0.5) * self.angular_spread
        self.sv = np.zeros((self.multi_paths, self.bs.n_antennas), dtype=complex)
        for i in range(self.multi_paths):
            self.sv[i, :] = np.exp(1j * np.pi * np.cos(self.aod[i]) * np.arange(self.bs.n_antennas)) \
                              / np.sqrt(self.bs.n_antennas)

    def _cal_csi_(self, ir_change):
        if ir_change:
            self.h = np.matmul(self.g, self.sv)
            self.H = self.h.reshape((Config().n_antennas, )) * np.sqrt(self.path_loss)

        self.gain = self.path_loss * np.square(np.linalg.norm(np.matmul(self.h, self.bs.code)))
        self.r_power = self.bs.power * self.gain

    def _check_is_link_(self):
        """ determine whether the channel is a direct link for data transmission or a interference channel, then
        initialize some extra attributes for the direct link. """

        if self.bs.index == self.ue.index:
            self.is_link = True
            self.utility, self.utility10, self.utility11, self.utility20, self.utility21 = None, None, None, None, None
            self.SINR, self.SINR10, self.SINR11, self.SINR20, self.SINR21 = None, None, None, None, None
            self.qoe, self.qoe10, self.qoe11, self.qoe20, self.qoe21 = None, None, None, None, None
            self.IN, self.IN10, self.IN11, self.IN20, self.IN21 = None, None, None, None, None
            self.interferer_neighbors, self.interferer_neighbors10, self.interferer_neighbors11, \
            self.interferer_neighbors20, self.interferer_neighbors21 = None, None, None, None, None
            self.interfered_neighbors, self.interfered_neighbors10, self.interfered_neighbors11, \
            self.interfered_neighbors20, self.interfered_neighbors21 = None, None, None, None, None
        else:
            self.is_link = False

    def _save_csi_(self, ir_change):
        """ save historical CSI """

        if ir_change:

            self.h2 = self.h1
            self.h1 = self.h

            self.r_power21 = self.r_power11
            self.r_power11 = self.r_power

            self.gain21 = self.gain11
            self.gain11 = self.gain

            if self.is_link:
                self.IN21 = self.IN11
                self.IN11 = self.IN

                self.SINR21 = self.SINR11
                self.SINR11 = self.SINR

                self.qoe21 = self.qoe11
                self.qoe11 = self.qoe

                self.utility21 = self.utility11
                self.utility11 = self.utility

                self.interferer_neighbors21 = self.interferer_neighbors11
                self.interferer_neighbors11 = self.interferer_neighbors

                self.interfered_neighbors21 = self.interfered_neighbors11
                self.interfered_neighbors11 = self.interfered_neighbors
        else:

            self.r_power20 = self.r_power10
            self.r_power10 = self.r_power

            self.gain20 = self.gain10
            self.gain10 = self.gain

            if self.is_link:
                self.IN20 = self.IN10
                self.IN10 = self.IN

                self.SINR20 = self.SINR10
                self.SINR10 = self.SINR

                self.qoe20 = self.qoe10
                self.qoe10 = self.qoe

                self.utility20 = self.utility10
                self.utility10 = self.utility

                self.interferer_neighbors20 = self.interferer_neighbors10
                self.interferer_neighbors10 = self.interferer_neighbors

                self.interfered_neighbors20 = self.interfered_neighbors10
                self.interfered_neighbors10 = self.interfered_neighbors

    def calculate_phi(self, h, k_u):
        # Add your own logic to calculate phi
        w = 180e3
        phi = h * w / k_u
        return phi

    def updatek(self):
        self.k_u = self.bs.k_u
        self.phi = self.calculate_phi(h=4, k_u=self.k_u)
        self.xi_req = np.random.uniform(low=0.8, high=0.9)  # Uniformly distributed between 0.8 and 0.9
        self.lambda_ = np.random.normal(loc=55,
                                        scale=2.5)  # Normally distributed with mean 55 and standard deviation 2.5
        self.w = np.random.uniform(low=0, high=1)
        self.phi_req = np.random.uniform(low=50, high=70)
        self.beta = np.random.normal(loc=0.2, scale=0.05 * 0.05)

    def update(self, ir_change):
        """ when the CSI is going to change due to the channel block fading or updating the beamformers, save the
        historical CSI and calculate the new CSI. parameter 'ir_change' is a bool variable which indicates the CSI
        changes due to the channel fading or not. """
        self._save_csi_(ir_change)
        if ir_change:
            # Fading
            e = (np.random.randn(1, self.multi_paths) + np.random.randn(1, self.multi_paths) * 1j) \
                * np.sqrt(1 - np.square(self.rho)) / np.sqrt(2)
            self.g = self.rho * self.g + e

        self._cal_csi_(ir_change)
