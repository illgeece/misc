#Fourier transform visualization
# Two sine waves, sum and fft them
# Time and frequency domain plots, three panel visualization saved to image format



using Plots
using FFTW
using DSP

function plot_sine_waves_and_fft(f1, f2, A1, A2, duration)
    # time vector
    t = 0:0.001:duration
    fs = 1/0.001  # sampling freq (Hz)
    
    # generate sine waves
    wave1 = A1 * sin.(2π * f1 * t)
    wave2 = A2 * sin.(2π * f2 * t)
    combined_wave = wave1 + wave2
    
    # compute FFT
    n = length(t)
    f = fft(combined_wave)
    freq = fftfreq(n, fs)
    
    # create subplots
    p1 = plot(t, wave1, label="Wave 1", 
             title="Individual Sine Waves",
             xlabel="Time (s)",
             ylabel="Amplitude",
             linewidth=2)
    plot!(t, wave2, label="Wave 2", linewidth=2)
    
    p2 = plot(t, combined_wave, 
             title="Combined Wave",
             xlabel="Time (s)",
             ylabel="Amplitude",
             linewidth=2)
    
    # plot magnitude spectrum
    p3 = plot(freq[1:div(n,2)], abs.(f)[1:div(n,2)],
             title="Frequency Spectrum",
             xlabel="Frequency (Hz)",
             ylabel="Magnitude",
             linewidth=2)
    
    # combine plots
    final_plot = plot(p1, p2, p3, layout=(3,1), size=(800, 1000))
    
    # save and display
    savefig(final_plot, "fourier_sine_waves.png")
    display(final_plot)
end

# get user input
println("Enter parameters for two sine waves:")
print("Frequency of first wave (Hz): ")
f1 = parse(Float64, readline())
print("Amplitude of first wave: ")
A1 = parse(Float64, readline())
print("Frequency of second wave (Hz): ")
f2 = parse(Float64, readline())
print("Amplitude of second wave: ")
A2 = parse(Float64, readline())
print("Duration of simulation (seconds): ")
duration = parse(Float64, readline())

# run simulation
plot_sine_waves_and_fft(f1, f2, A1, A2, duration) 