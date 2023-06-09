import numpy as np
import matplotlib.pyplot as plt
from time import time
import timeit
from movespad import laser, bkg, spad, params as pm, pixel
from movespad import spad


def main():

    offset = 2* pm.Z / pm.C
    time_step = 100e-12
    start, stop = 0, pm.PULSE_DISTANCE * pm.N_IMP
    n_steps = int((stop-start)/time_step)
    times = np.linspace(start, stop, n_steps)
    bw = 1 #points --> 50 ps

    print("Creating bkg events...")
    bkg_spec = bkg.bkg_spectrum(times, pm.TAU_OPT, pm.RHO_TGT, pm.FF,
                                pm.PIXEL_AREA, pm.Z, pm.F_LENS,
                                pm.D_LENS,pm.BKG_POWER)
    
    print("Creating laser events...")
    las_spec = laser.full_laser_spectrum(offset, time_step, pm.N_IMP, pm.TAU_OPT,
                        pm.RHO_TGT, pm.FF, pm.PIXEL_AREA, pm.F_LENS,
                        pm.D_LENS, pm.THETA_H, pm.THETA_V, pm.Z,
                        pm.PULSE_DISTANCE, pm.SIGMA_LASER, pm.PULSE_ENERGY)


    print("Extracting number of laser photons...")
    n_ph_las, t_laser = laser.get_n_photons(times, las_spec, bw)
    print("Extracting number of bkg photons...")
    n_ph_bkg, t_bkg = bkg.get_n_photons_bkg(times, bkg_spec, bw)

    pix = pixel.Pixel(size = pm.PIXEL_SIZE)

    pix.create_and_split(t_laser, t_bkg, pm.PDP)
    print("Generating crosstalk...")
    pix.crosstalk(pm.XTALK_PROBS)
    print("Applying t dead filter...")
    pix.t_dead_filter(pm.T_DEAD, pm.PDP, pm.AP_PROB)
    print("Applying SPAD jitter...")
    pix.spad_jitter(pm.SPAD_JITTER)
    print(f"Photon count: {[len(ts.timestamps) for ts in pix.timestamps]}")
    print(f"Laser count: {[len([elem for elem in ts.timestamps if elem.type=='las']) for ts in pix.timestamps]}")

    print("Applying coincidence...")
    survived = pix.coincidence(thr=pm.COINCIDENCE_THR, window=3*pm.SIGMA_LASER)
    print("Plotting results:")
    pix.plot_events(times, las_spec, survived)

    hist_data = laser.get_hist_data([s.time for s in survived], pm.PULSE_DISTANCE)

    fig, ax = plt.subplots()
    ax.hist(hist_data, bins=[i*1e-9 for i in range(0,1350)])

    secax = ax.secondary_xaxis(location='top', functions=(lambda x: 0.5*x*pm.C, lambda x : 2*x/pm.C))
    secax.set_label("Distance [m]")
    plt.title(f"Histogram ({pm.N_IMP} pulses)")
    plt.show()


def execute_main(
    params: dict 
):

    las_power, las_sigma = float(params['laser_power']), float(params['laser_sigma'])*10**(-9)
    pixel_size, pdp = int(params['pixel_size']), float(params['pdp'])
    pixel_area, ff = (float(params['spad_size'])*10**(-6)*pixel_size)**2, float(params['fill_factor'])

    pulse_distance = float(params['pulse_distance'])*10**-6
    theta_h, theta_v = float(params['theta_h'])/1000, float(params['theta_v'])/1000

    f_lens, d_lens = float(params['f_lens'])/1000, float(params['d_lens'])/1000
    tau, bkg_pow = float(params['tau']), float(params['bkg_power'])*10*1.20
    t_dead, thr = float(params['t_dead'])*10**-9, int(params['coinc_thr'])

    n_imp, z = int(params['n_imp']), float(params['z'])
    rho_tgt, rng_min = float(params['rho_tgt']), float(params['range_min'])

    spad_j, tdc_j = float(params['spad_j'])*10**-12, float(params['tdc_j'])*10**-12
    n_bit_tdc, n_bit_hist  = int(params['n_bit_tdc']), int(params['n_bit_hist'])

    pulse_energy = np.sqrt(2*pm.PI)*las_sigma*las_power

    offset = 2*z / pm.C
    time_step = 100e-12
    start, stop = 0, pulse_distance * n_imp
    n_steps = int((stop-start)/time_step)
    times = np.linspace(start, stop, n_steps)
    bw = 1

    print("Creating bkg events...")
    bkg_spec = bkg.bkg_spectrum(times, tau, rho_tgt, ff,
                                pixel_area, z, f_lens, d_lens, bkg_pow )
    print("Creating laser events...")
    las_spec = laser.full_laser_spectrum(offset, time_step, n_imp, tau, rho_tgt,
                        ff, pixel_area, f_lens, d_lens, theta_h, theta_v,
                        z, pulse_distance, las_sigma, pulse_energy)

    print("Extracting number of laser photons...")
    n_ph_las, t_laser = laser.get_n_photons(times, las_spec, bw)
    print("Extracting number of bkg photons...")
    n_ph_bkg, t_bkg = bkg.get_n_photons_bkg(times, bkg_spec, bw)

    pix = pixel.Pixel(size = pixel_size)

    pix.create_and_split(t_laser, t_bkg, pdp)
    print("Generating crosstalk...")
    pix.crosstalk(pm.XTALK_PROBS)
    print("Applying t dead filter...")
    pix.t_dead_filter(t_dead, pdp, pm.AP_PROB)

    print(f"Photon count: {[len(ts.timestamps) for ts in pix.timestamps]}")
    print(f"Laser count: {[len([elem for elem in ts.timestamps if elem.type=='las']) for ts in pix.timestamps]}")

    print("Applying SPAD jitter...")
    pix.spad_jitter(spad_j)
    print("Applying coincidence...")
    survived = pix.coincidence(thr=thr, window=3*las_sigma)

    survived = pixel.Pixel.tdc_jitter(tdc_j, survived).tolist()
    
    print(f"{len(survived)} events found")
    print("Plotting results:")
    pix.plot_events(times, las_spec, survived)
    if len(survived)==0:
        plt.show()
        return
    
    tot_n = 2**(n_bit_tdc)-1
    count_limit = 2**(n_bit_hist)-1
    t_min = 2*rng_min / pm.C
    bins = np.linspace(t_min, pulse_distance, tot_n)
    hist_data = laser.get_hist_data([s.time for s in survived], pulse_distance)

    fig, ax = plt.subplots()
    counts, bins = np.histogram(hist_data, bins=bins)

    counts = [min(count_limit, c) for c in counts]

    ax.stairs(counts, bins)

    secax = ax.secondary_xaxis(location='top', functions=(lambda x: 0.5*x*pm.C, lambda x : 2*x/pm.C))
    secax.set_label("Distance [m]")
    plt.title(f"TOF histogram {n_imp} pulses")
    plt.show()


if __name__ == '__main__':
    main()