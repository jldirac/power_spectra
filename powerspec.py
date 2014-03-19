import argparse
import math
import numpy as np
from scipy import fftpack
from astropy.io import fits

"""
		powerspec.py

Makes a power spectrum out of event-mode data from RXTE.

datafile - str - Name of FITS file with photon count rate data.
outfile - str - Name of file which the table of power spectral data will be written to.
rebinned_outfile - str - Name of file which the table of rebinned power spectral data will
						  be written to.
seconds - int - Number of seconds each segment of the light curve should be
rebin_const - float - Used to re-bin the data geometrically after the average power is 
					   computed, such that bin_size[n+1] = bin_size[n] * rebin_const

Written in Python 2.7 by A.L. Stevens, A.L.Stevens@uva.nl, 2013-2014

All scientific modules imported above, as well as python 2.7, can be downloaded in the 
Anaconda package, https://store.continuum.io/cshop/anaconda/
I don't think argparse came with Anaconda, but I don't remember installing anything 
special to get them.

"""

#################################################
## Determines if 'num' is a power of 2 (>= 1)
##  Returns 'True' if 'num' is a power of 2, 
##  Returns 'False' if 'num' is not a power of 2
#################################################
def power_of_two(num):
	n = int(num)
	x = 2.0
	
	if n == 1.0:
		return True
	else: 
		while x < n and x < 2147483648:
			x *= 2
		return n == x
		
	## End of function 'power_of_two'



#############################################################################
## Re-bins the power spectrum in frequency space by some re-binning constant
#############################################################################
def geometric_rebinning(rms_power_avg, rms_err_power, freq, rebin_const, length_of_list):
	""" 
			geometric_rebinning
			
		Re-bins the fractional rms power spectrum in frequency space by some re-binning
		constant (rebin_const>1). 
		
		Passed: rms_power_avg - list of floats - Fractional rms power, averaged over all
												   segments in the light curve
				rms_err_power - list of floats - Error on the rms power
				freq - list of floats - Frequencies (in Hz) corresponding to the power 
										 spectrum
				rebin_const - float - Constant >1 by which we want to re-bin the spectrum,
									   such that bin_size[n+1] = bin_size[n] * rebin_const
				length_of_list - int - Length of the original power spectrum (only the 
										positive frequencies)
		
		Returns: rebinned_freq - list of floats - Frequencies of power spectrum re-binned
				 								   according to rebin_const
				 rebinned_rms_power - list of floats - Power spectrum re-binned according
				 										 to rebin_const
				 err_rebinned_power - list of floats - Error on the re-binned rms power
	
	"""
	
	## Initializing variables
	rebinned_rms_power = []  # List of re-binned fractional rms power
	rebinned_freq = []       # List of re-binned frequencies
	err_rebinned_power = []  # List of error in re-binned power
	real_index = 1.0		 # The unrounded next index in power_avg
	int_index = 1			 # The int of real_index, added to current_m every iteration
	current_m = 1 			 # Current index in power_avg
	prev_m = 0				 # Previous index m
	bin_power = 0.0			 # The power of the current re-binned bin
	bin_freq = 0.0			 # The frequency of the current re-binned bin
	err_bin_power2 = 0.0	 # 
	bin_range = 0.0			 # The range of un-binned bins covered by this re-binned bin
	
	
	## Looping through the length of the array power_avg, geometric bin by geometric bin, 
	##  to compute the average power and frequency of that geometric bin
	## Equations for frequency, power, and error on power are from Adam's thesis
	while current_m < length_of_list:
# 	while current_m < 400: # used for debugging
		
		## Initializing clean variables for each iteration of the while-loop
		bin_power = 0.0 # the averaged power at each index of rebinned_power
		err_bin_power2 = 0.0 # the square of the errors on the powers in this bin
		bin_range = 0.0
		bin_freq = 0.0
		
# 		print "Current_m = %d, prev_m = %d, real_index = %f, int_index = %d" % (current_m, prev_m, real_index, int_index)

		## Looping through the data points contained within one geometric bin
		for k in range (prev_m, current_m):
			## Adding power data points (tiny linear bins) within a geometric bin
			##  After the while-loop, this will be divided by total number of data points
			bin_power += rms_power_avg[k]
			## Also computing error in bin power squared, for error computation later
			err_bin_power2 += rms_err_power[k] ** 2
			## End of for-loop
		
		## Determining the range of indices this specific geometric bin covers
		bin_range = abs(current_m - prev_m)
		
		## Dividing bin_power (currently just a sum of the data points) by the number 
		##  of points to get an arithmetic average
		bin_power /= float(bin_range)
		
		## Computing the mean frequency of a geometric bin
		bin_freq = ((freq[current_m] - freq[prev_m]) / bin_range) + freq[prev_m]
		
		## If there's only one data point in the geometric bin, there's no need to take
		##  an average. This also prevents it from skipping the first data point.
		if bin_range == 1:
			bin_power = rms_power_avg[prev_m]
			bin_freq = freq[prev_m]
		
		## Appending values to arrays
		rebinned_rms_power.append(bin_power)
		rebinned_freq.append(bin_freq)
		## Computing error in geometric bin -- equation from Adam's thesis
		err_rebinned_power.append(math.sqrt(err_bin_power2) / float(bin_range))
		
		## Incrementing for the next iteration of the loop
		prev_m = current_m
		real_index *= rebin_const
		int_index = int(round(real_index))
		current_m += int_index
		
		## Since the for-loop goes from prev_m to current_m-1 (since that's how the range 
		##  function works) it's ok that we set prev_m = current_m here for the next 
		##  round. This will not cause any double-counting of bins or missing bins.
		
		## End of while-loop
		
	return rebinned_freq, rebinned_rms_power, err_rebinned_power
	
	## End of function 'geometric_rebinning'

########################################################################################
## Writes power spectrum and geometrically re-binned power spectrum to two output files
########################################################################################
def output(out_file, rebinned_out_file, fits_file, dt, n_bins, num_segments, \
		   mean_rate_whole, freq, rms_power_avg, rms_err_power, rebin_const, \
		   rebinned_freq, rebinned_rms_power, err_rebinned_power):
	""" 
			output
			
		Writes power spectrum and re-binned power spectrum to two output files.
		
		Passed: out_file - str - Name of output file for standard power spectrum
				rebinned_out_file - str - Name of output file for geometrically re-binned 
										   power spectrum
				fits_file - str - Name of FITS file containing input data
				dt - float - Size of time bin, in seconds (must be power of 2)
				n_bins - int - Number of time bins in a segment (must be power of 2)
				num_segments - int - Number of segments in the light curve
				mean_rate_whole - float - Mean rate of the all light curves used.
				freq - list of floats - Frequencies (in Hz) corresponding to the power 
										 spectrum
				rms_power_avg - list of floats - Fractional rms power, averaged over all 
												  segments of the light curve and all
												  light curves.
				rms_err_power - list of floats - Error on avg fractional rms power
				rebin_const - float - Constant >1 by which we want to re-bin the spectrum,
									   such that bin_size[n+1] = bin_size[n] * rebin_const
				rebinned_freq - list of floats - Frequencies of power spectrum re-binned
				 								  according to rebin_const
				rebinned_rms_power - list of floats - Power spectrum re-binned according
				 									   to rebin_const
				err_rebinned_power - list of floats - Error on re-binned fractional rms 
													   power

		Returns: nothing
	
	"""
	
	print "Output sent to %s" % out_file
	
	## First, the standard linear output
	out = open (out_file, 'w')
	
	## Writing a header
	out.write("#\t\tPower spectrum")
	out.write("\n# Data: %s" % fits_file)
	out.write("\n# Time bin size = %.12f seconds" % dt)
	out.write("\n# Number of bins per segment = %d" % n_bins)
	out.write("\n# Number of segments per light curve = %d" % num_segments)
	out.write("\n# Duration of light curve used = %d seconds" % (num_segments * n_bins * dt))
	out.write("\n# Mean count rate = %.8f, over whole light curve" % mean_rate_whole)
	out.write("\n# ")
	out.write("\n# Column 1: Frequency in Hz (sample_frequency * 1.0/dt)")
	out.write("\n# Column 2: Fractional rms normalized mean power")
	out.write("\n# Column 3: Fractional rms normalized error on the mean power")
	out.write("\n# ")
	
	## Writing a table containing data computed above
	for k in range(0, len(freq)):
		if freq[k] >= 0:
			out.write("\n%.8f\t%.8f\t%.8f" % (freq[k], rms_power_avg[k], rms_err_power[k]))
			## End of if-statement
		## End of for-loop
		
	out.close()
	
	## Now outputting the geometric-binned data
	##  Need to do this separately since it has a different number of data points from
	##  the standard un-binned power spectrum.
	
	print "and %s" % rebinned_out_file # continuation of 'output sent to' print stmt above
	
	out = open (rebinned_out_file, 'w')
	
	## Writing a header
	out.write("#\t\tPower spectrum")
	out.write("\n# Data: %s" % fits_file)
	out.write("\n# Geometrically re-binned in frequency at (%lf * previous bin size)" % rebin_const)
	out.write("\n# Corresponding un-binned output file: %s" % out_file)
	out.write("\n# Original time bin size = %.12f seconds" % dt)
	out.write("\n# Duration of light curve used = %d seconds" % (num_segments * n_bins * dt))
	out.write("\n# Mean count rate = %.8f, over whole light curve" % mean_rate_whole)
	out.write("\n# ")
	out.write("\n# Column 1: Frequency in Hz")
	out.write("\n# Column 2: Fractional rms normalized mean power")
	out.write("\n# Column 3: Error in fractional rms normalized mean power")
	out.write("\n# ")
	
	## Writing a table containing data computed above
	for k in range(0, len(rebinned_freq)):
		if rebinned_freq[k] >= 0:
			out.write("\n%.8f\t%.8f\t%.8f" % (rebinned_freq[k], rebinned_rms_power[k], err_rebinned_power[k]))
			## End of if-statement
		## End of for-loop
	
	out.close()
	## End of function 'output'


###################################################################################
## Reads in a FITS file, takes FFT of data, makes power spectrum, writes to a file
###################################################################################
def main(fits_file, out_file, rebinned_out_file, num_seconds, rebin_const):
	""" 
			make_powerspec
			
		Reads in a FITS file, takes FFT of segments of light curve data, computes power 
		of each segment, averages power over all segments, writes data to a file.  
		Recommended for use with plot_powerspec.py and plot_geom_powerspec.py. 
	
	Passed: fits_file - str - Name of input file (in FITS format) of type .lc made in 
							   HEASOFT's seextrct
			out_file - str - Name of output file for standard power spectrum
			rebinned_out_file - str - Name of output file for re-binned power spectrum
			ns - int - Number of seconds each segment of the light curve should be
			rbc - float - Used to re-bin the data geometrically after the average 
								  power is computed, such that 
							      bin_size[n+1] = bin_size[n] * rebin_const
	
	Returns: nothing
	
	"""
	pass
	
	## Idiot checks, to ensure that our assumptions hold
	assert num_seconds > 0 # num_seconds must be a positive integer
	assert rebin_const >= 1.0 # rebin_const must be a float greater than 1
	assert power_of_two(num_seconds) # num_seconds must be a power of 2 for the FFT -
									 #  calls the above function 'power_of_two'
	
# 	print "Opening the fits file"
	## Opens the fits file using the Astropy library 'fits.open'.
	hdulist = fits.open(fits_file)
	
	## Print out the basic info on structure of FITS file.
# 	print hdulist.info()
	
# 	print "Getting the header"
	## Read the header information from the FITS file into 'header'.
	header = fits.getheader(fits_file)	
	
	## Get the data from the FITS file.
	## Need to select which extension to use/extract.
	## Usually, 1 is the photon count rate, 2 is the std GTI
	## But check the header info to be safe
	print "Reading in data from", fits_file
	fits_data = hdulist[1].data
	
	## Finds the timestep of each bin and number of bins needed for a segment of data
	dt = fits_data[1].field(0) - fits_data[0].field(0) # in seconds
	n_bins = num_seconds * int(1.0 / dt)
	
	## Printing info on structure/binning of the data.
	print "Time bin size =", dt, "seconds"
# 	print "Number of bins per segment =", n_bins
	
	## Initializing the average power and mean count rate of the whole data set
	power_avg = [0.0 for x in range(0, n_bins)]
	mean_rate_whole = 0

	## Initializing loop control variables
	i = 0 # start of bin index to make segment of data for inner for-loop
	j = n_bins # end of bin index to make segment of data for inner for-loop
	num_segments = 0 # counting how many times the while-loop iterates, so we can take the avg
		
	## if getting a 'rate referenced before assignment' error, the program isn't making it 
	##  into the while-loop
	print "Extracting data from FITS file and taking the FFT."
	print "Segments computed:"
	## Looping through length of data file, segment by segment, to compute power for each 
	##  data point in the segment
# 	print len(fits_data.field(1))
	
	while j < len(fits_data.field(1)): # so 'j' doesn't overstep the length of the file
# 	while num_segments < 2:  # used for testing, so the while-loop does 1 iteration
		
		## Initializing clean variables for each iteration of the while-loop
		rate = []
		power_segment = []
		fft_data = []
		mean_rate_segment = 0;
		
		## Printing out which segment we're on every x segments
 		if num_segments % 100 == 0:
			print "\t",num_segments
			
		## Making a 'num_seconds'-long segment of data

#		print "Getting segment"	
		## Extracts the second column of 'fits_data' and assigns it to 'rate'. 
		## Don't be a dumbass. Don't use a for-loop.
		rate = fits_data[i:j].field(1)
				
		## Computing the mean flux (probably in photon count rate) of the segment
		mean_rate_segment = np.mean(rate)
		
		## Subtracting the mean rate off each value of 'rate'
		##  This eliminates the spike at 0 Hz 
		rate_sub_mean = [x - mean_rate_segment for x in rate]
		
		## Taking the 1-dimensional FFT of the time-domain photon count rate
		##  Returns 'fft_data' as a complex-valued list
		##  Using the SciPy FFT algorithm, as it is faster than NumPy for large lists
		fft_data = fftpack.fft(rate_sub_mean)

		## Computing the power
		power_segment = np.absolute(fft_data)**2
		
		## Adding segments to the average
		##  After the while-loop, average will be divided by total number of segments
		power_avg = [a+b for a,b in zip(power_segment, power_avg)]	
		mean_rate_whole += mean_rate_segment
		
		## Incrementing the counters and indices
		i = j
		j += n_bins
		num_segments += 1
		## Since the for-loop goes from i to j-1 (since that's how the range function 
		##  works) it's ok that we set i=j here for the next round. This will not cause 
		##  any double-counting of rows or missing rows.
		
		## End of while-loop
	
	
	## Dividing these (currently just a sum of the segments) by the number of segments
	##  to get an arithmetic average
	power_avg = [x / float(num_segments) for x in power_avg]
	mean_rate_whole /= float(num_segments)
# 	print "Power spectrum computed"
	
	## Making integer time bins to plot against. Giving 't' as many data points as 'rate'
	t = np.arange(int(len(rate)))
	
	## Computing the FFT sample frequencies
	##  Returns the frequency bins in cycles/unit starting at zero, given a window length 
	##  't'
	sample_freq = np.fft.fftfreq(t.shape[-1])

	## Changing sample frequency to Hz
	freq = [x * int(1.0 / dt) for x in sample_freq]
		
	## Ensuring that we're only using and saving the positive frequency values 
	##  (and associated power values)
	max_index = freq.index(max(freq))
	freq = freq[0:max_index+1] # So that we don't cut off the last positive data
	                           #  point, since it cuts from 0 to end-1
	power_avg = power_avg[0:max_index+1]
	
	## Computing the error on the mean power
	err_power = [x / math.sqrt(float(num_segments)*len(power_avg)) for x in power_avg]
	
	## Leahy normalization
	leahy_power_avg = [(2.0 * x * dt / ((1.0/dt) * num_seconds) / mean_rate_whole) for x in power_avg]
	
	## Fractional rms normalization
	rms_power_avg = [(2.0 * x * dt / ((1.0/dt) * num_seconds) / mean_rate_whole**2) - (2.0 / mean_rate_whole) for x in power_avg]
# 	other_rms_power_avg = [(x / mean_rate_whole) - (2.0 / mean_rate_whole) for x in leahy_power_avg] # This gives the same values as the above line, as checked below
	
	"""
	## Troubleshooting -- not a problem!
	x = 0
	while x < len(rms_power_avg):
		if abs(rms_power_avg[x] - other_rms_power_avg[x]) > 10**-14:
			print "Issue:", x, rms_power_avg[x], other_rms_power_avg[x]
		x += 1
	print ""
	"""

	## Error on fractional rms power -- don't trust this equation (yet)
	rms_err_power = [(2.0 * x * dt / ((1.0/dt) * num_seconds) / mean_rate_whole**2) for x in err_power]

	## Initializing variables for the re-binned spectra
	rebinned_rms_power = []
	rebinned_freq = []
	err_rebinned_power = []
	length_of_list = len(power_avg)
	
	## Calling the above function for geometric re-binning
	rebinned_freq, rebinned_rms_power, err_rebinned_power = geometric_rebinning(\
		rms_power_avg, rms_err_power, freq, rebin_const, length_of_list)
	print "everything's fine, num_seg = %d" % num_segments
	## Calling the above function for writing to output files
	output(out_file, rebinned_out_file, fits_file, dt, n_bins, num_segments, \
		mean_rate_whole, freq, rms_power_avg, rms_err_power, rebin_const, rebinned_freq, \
		rebinned_rms_power, err_rebinned_power)

	
	## End of function 'main'



#################################################
## Parsing cmd-line arguments and calling 'main'
#################################################

if __name__ == "__main__":
	
	parser = argparse.ArgumentParser()
	parser.add_argument('datafile', help="The full path of the FITS file with RXTE event mode data, with time in column 1 and rate in column 2.")
	parser.add_argument('outfile', help="The full path of the (ASCII/txt) file to write the frequency and power to.")
	parser.add_argument('rebinned_outfile', help="The full path of the (ASCII/txt) file to write the geometrically re-binned frequency and power to.")
	parser.add_argument('seconds', type=int, help="Duration of segments the light curve is broken up into, in seconds. Must be an integer power of two.")
	parser.add_argument('rebin_const', type=float, help="Float constant by which we geometrically re-bin the power spectrum.")
	args = parser.parse_args()

	main(args.datafile, args.outfile, args.rebinned_outfile, args.seconds, args.rebin_const)

## End of program 'powerspec.py'
