"""Create emission spectrum of the laser"""

import numpy as np
import matplotlib.pyplot as plt
from movespad import params as pm
from tqdm import tqdm, trange


def gauss_1d(arr: np.ndarray, mean: float, sig: float) -> np.ndarray:
    """Normalized gaussian"""
    return 1 / (sig *np.sqrt(2*pm.PI)) * np.exp(-np.power(arr - mean, 2.) / (2 * np.power(sig, 2.)))


def _base_laser_spectrum(times: np.ndarray, mean, sigma, pulse_energy) -> np.ndarray:
    """Generate single gaussian"""
    return gauss_1d(times, mean, sigma) * pulse_energy
 

def full_laser_spectrum(init_offset, time_step, n_imps, tau, rho_tgt,
                        ff, pixel_area, f_lens, d_lens, theta_h, theta_v,
                        z, pulse_distance, sigma_laser, pulse_energy):
    """
    Returns the normalized power spectrum of the laser.
    See Eq. 9 on the FBK paper

    """

    num = tau * rho_tgt * ff * pixel_area
    den = pm.PI * (f_lens/d_lens)**2 * np.tan(0.5 * theta_h)* np.tan(0.5 * theta_v) * (d_lens**2 + 4*z**2)

    base_len =  int(pulse_distance / time_step)

    full_spec = []

    for i in trange(n_imps, leave=False):
        mean = init_offset + i * pulse_distance
        base_spec = np.linspace(i*pulse_distance, (i+1)*pulse_distance, base_len)
        single_gauss = _base_laser_spectrum(base_spec, mean, sigma_laser, pulse_energy)

        full_spec.extend(single_gauss)

    pdf = np.asarray(full_spec) * num / den

    return pdf


def get_n_photons(times: np.ndarray, spectrum: np.ndarray, bin_width: int):
    """Return number of photons generated for each bin.
    Photons are generated according to a Poisson process"""

    delta_t = times[bin_width] - times[0]

    n_ph_mean = get_mean_n_ph(spectrum, delta_t, bin_width)

    n_ph = np.asarray([
        np.random.poisson(lmbd) for lmbd in n_ph_mean
    ])

    return n_ph, times[::bin_width][n_ph >= 1]


def get_mean_n_ph(spectrum, delta_t, bin_width) -> np.ndarray:
    """Return expected number of photons for each time bin."""
    tot_energies = np.asarray([s*delta_t for s in spectrum[::bin_width]])
    return tot_energies / pm.E_PH


def plot_spectrum(times, spectrum, ax, label):
    """Plot laser and bkg spectrum"""
    ax.plot(times, spectrum, label=label)


def get_hist_data(times: list, clock: float):

    if len(times)==0:
        return
    res = [times[0]%clock]

    for i, time in enumerate(times):
        if i==0:
            continue

        if times[i]//clock == times[i-1]//clock:
            continue
        else:
            res.append(time%clock)

    return res


if __name__ == '__main__':

    print(get_hist_data([1,13,14,15,34,36,42], 10)    )