# Iron-Core Diode V-I Characteristics vs Frequency Analysis
# Models frequency-dependent behavior of an iron-core diode at 26°C
# Includes parasitic effects, core saturation, and magnetic losses

using Plots
using LinearAlgebra
using Printf

# Physical constants
const k_B = 1.380649e-23  # Boltzmann constant (J/K)
const q = 1.602176634e-19  # Elementary charge (C)
const T = 299.15  # Temperature in Kelvin (26°C)

# Diode parameters structure
struct IronCoreDiodeParams
    I_s::Float64        # Saturation current (A)
    n::Float64          # Ideality factor
    R_s::Float64        # Series resistance (Ω)
    C_j::Float64        # Junction capacitance (F)
    L_core::Float64     # Core inductance (H)
    R_core::Float64     # Core resistance (Ω)
    B_sat::Float64      # Core saturation flux density (T)
    A_core::Float64     # Core cross-sectional area (m²)
    N_turns::Int        # Number of turns in core winding
end

# Default iron-core diode parameters
function default_diode_params()
    return IronCoreDiodeParams(
        1e-12,    # I_s: 1 pA
        1.2,      # n: ideality factor
        0.1,      # R_s: 0.1 Ω series resistance
        100e-12,  # C_j: 100 pF junction capacitance
        10e-6,    # L_core: 10 μH core inductance
        0.05,     # R_core: 0.05 Ω core resistance
        0.3,      # B_sat: 0.3 T saturation flux density
        1e-6,     # A_core: 1 mm² core area
        10        # N_turns: 10 turns
    )
end

# Calculate frequency-dependent impedance effects
function calc_frequency_effects(params::IronCoreDiodeParams, frequency::Float64)
    ω = 2π * frequency
    
    # Capacitive reactance (reduces effective voltage at high frequencies)
    X_c = frequency > 0 ? -1/(ω * params.C_j) : -Inf
    
    # Inductive reactance from iron core
    X_l = ω * params.L_core
    
    # Core loss resistance (frequency dependent)
    # Core losses increase with frequency due to eddy currents and hysteresis
    R_core_eff = params.R_core * (1 + frequency/1000)  # Simplified model
    
    # Total series impedance
    Z_series = params.R_s + R_core_eff + 1im * (X_l + X_c)
    
    # Magnitude and phase
    Z_mag = abs(Z_series)
    Z_phase = angle(Z_series)
    
    return Z_mag, Z_phase, R_core_eff
end

# Core saturation effects
function calc_core_saturation_factor(params::IronCoreDiodeParams, current::Float64)
    # Magnetic flux in core
    Φ = current * params.L_core / params.N_turns
    
    # Flux density
    B = Φ / params.A_core
    
    # Saturation factor (reduces inductance as core saturates)
    if abs(B) >= params.B_sat
        sat_factor = 0.1  # Heavily saturated
    else
        sat_factor = 1.0 - (abs(B) / params.B_sat)^2
    end
    
    return sat_factor
end

# Modified diode equation with frequency effects
function diode_current(voltage::Float64, params::IronCoreDiodeParams, frequency::Float64)
    if voltage < -5.0  # Breakdown region
        return -1e3 * voltage  # Simple breakdown model
    end
    
    # Get frequency effects
    Z_mag, Z_phase, R_eff = calc_frequency_effects(params, frequency)
    
    # Effective voltage across junction (reduced by series impedance)
    V_eff = voltage * params.R_s / (params.R_s + R_eff)
    
    # Basic diode equation
    V_thermal = k_B * T / q  # Thermal voltage (~25.9 mV at 26°C)
    
    if V_eff > 0
        I_basic = params.I_s * (exp(V_eff / (params.n * V_thermal)) - 1)
    else
        I_basic = -params.I_s * (exp(-V_eff / (params.n * V_thermal)) - 1)
    end
    
    # Apply core saturation effects for higher currents
    if abs(I_basic) > 1e-6  # Only for significant currents
        sat_factor = calc_core_saturation_factor(params, I_basic)
        I_basic *= sat_factor
    end
    
    # Frequency-dependent current reduction due to reactive effects
    freq_factor = 1.0 / (1.0 + (frequency / 1e6)^2)  # Roll-off at ~1 MHz
    
    return I_basic * freq_factor
end

# Generate V-I curve for given frequency
function generate_vi_curve(params::IronCoreDiodeParams, frequency::Float64, voltage_range::AbstractRange)
    voltages = collect(voltage_range)
    currents = [diode_current(v, params, frequency) for v in voltages]
    return voltages, currents
end

# Main analysis function
function analyze_iron_core_diode_vs_frequency()
    println("Iron-Core Diode V-I Characteristics vs Frequency Analysis")
    println("Temperature: 26°C")
    println("="^60)
    
    # Initialize diode parameters
    params = default_diode_params()
    
    # Display parameters
    println("\nDiode Parameters:")
    println("Saturation current (I_s): $(params.I_s*1e12) pA")
    println("Ideality factor (n): $(params.n)")
    println("Series resistance (R_s): $(params.R_s) Ω")
    println("Junction capacitance (C_j): $(params.C_j*1e12) pF")
    println("Core inductance (L_core): $(params.L_core*1e6) μH")
    println("Core resistance (R_core): $(params.R_core) Ω")
    println("Core saturation (B_sat): $(params.B_sat) T")
    
    # Frequency range for analysis
    frequencies = [0.0, 1e3, 10e3, 100e3, 1e6, 10e6]  # DC to 10 MHz
    freq_labels = ["DC", "1 kHz", "10 kHz", "100 kHz", "1 MHz", "10 MHz"]
    
    # Voltage range
    voltage_range = -1.0:0.01:1.5
    
    # Generate curves for each frequency
    println("\nGenerating V-I curves...")
    curves = []
    for (i, freq) in enumerate(frequencies)
        voltages, currents = generate_vi_curve(params, freq, voltage_range)
        push!(curves, (voltages, currents, freq_labels[i]))
        
        # Print some key characteristics
        forward_bias_idx = findfirst(v -> v ≈ 0.7, voltages)
        if forward_bias_idx !== nothing
            I_forward = currents[forward_bias_idx]
            println("$(freq_labels[i]): I @ 0.7V = $(@sprintf("%.3e", I_forward)) A")
        end
    end
    
    # Create comprehensive plot
    println("\nCreating plots...")
    
    # Main V-I characteristic plot (linear scale)
    p1 = plot(title="Iron-Core Diode V-I Characteristics vs Frequency",
              xlabel="Voltage (V)",
              ylabel="Current (A)",
              legend=:topleft,
              size=(800, 600))
    
    colors = [:blue, :red, :green, :purple, :orange, :brown]
    for (i, (voltages, currents, label)) in enumerate(curves)
        plot!(p1, voltages, currents, 
              label=label, 
              linewidth=2, 
              color=colors[i])
    end
    
    # Logarithmic plot for better visualization of low currents
    p2 = plot(title="Iron-Core Diode V-I Characteristics (Log Scale)",
              xlabel="Voltage (V)",
              ylabel="Current (A)",
              yscale=:log10,
              legend=:topleft,
              size=(800, 600))
    
    for (i, (voltages, currents, label)) in enumerate(curves)
        # Filter out zero and negative currents for log plot
        valid_idx = currents .> 1e-15
        if any(valid_idx)
            plot!(p2, voltages[valid_idx], currents[valid_idx], 
                  label=label, 
                  linewidth=2, 
                  color=colors[i])
        end
    end
    
    # Frequency response at fixed voltage
    p3 = plot(title="Current vs Frequency @ V = 0.7V",
              xlabel="Frequency (Hz)",
              ylabel="Current (A)",
              xscale=:log10,
              yscale=:log10,
              legend=:topright,
              size=(800, 600))
    
    test_voltage = 0.7
    freq_currents = [diode_current(test_voltage, params, f) for f in frequencies[2:end]]  # Skip DC
    plot!(p3, frequencies[2:end], abs.(freq_currents), 
          marker=:circle, 
          linewidth=2, 
          label="I @ 0.7V")
    
    # Impedance vs frequency plot
    p4 = plot(title="Series Impedance vs Frequency",
              xlabel="Frequency (Hz)",
              ylabel="Impedance Magnitude (Ω)",
              xscale=:log10,
              yscale=:log10,
              legend=:bottomright,
              size=(800, 600))
    
    freq_range = 10 .^ (1:0.1:7)  # 10 Hz to 10 MHz
    impedances = [calc_frequency_effects(params, f)[1] for f in freq_range]
    plot!(p4, freq_range, impedances, 
          linewidth=2, 
          label="Total Series Z")
    
    # Combine all plots
    final_plot = plot(p1, p2, p3, p4, layout=(2,2), size=(1600, 1200))
    
    # Save and display
    savefig(final_plot, "iron_core_diode_frequency_analysis.png")
    display(final_plot)
    
    # Performance analysis
    println("\nFrequency Performance Analysis:")
    println("-"^40)
    
    dc_current = diode_current(0.7, params, 0.0)
    for (i, freq) in enumerate(frequencies[2:end])
        current = diode_current(0.7, params, freq)
        reduction = (1 - current/dc_current) * 100
        Z_mag, _, _ = calc_frequency_effects(params, freq)
        
        println("$(freq_labels[i+1]):")
        println("  Current reduction: $(@sprintf("%.1f", reduction))%")
        println("  Series impedance: $(@sprintf("%.3f", Z_mag)) Ω")
    end
    
    return curves, final_plot
end

# Additional utility function for custom frequency analysis
function custom_frequency_analysis(custom_frequencies::Vector{Float64})
    params = default_diode_params()
    voltage_range = -1.0:0.05:1.5
    
    println("Custom Frequency Analysis:")
    for freq in custom_frequencies
        voltages, currents = generate_vi_curve(params, freq, voltage_range)
        
        # Find current at 0.7V
        idx = findfirst(v -> v ≈ 0.7, voltages)
        if idx !== nothing
            println("Frequency: $(@sprintf("%.0f", freq)) Hz, I @ 0.7V: $(@sprintf("%.3e", currents[idx])) A")
        end
    end
end

# Run the main analysis
println("Starting Iron-Core Diode Analysis...")
curves, plot_result = analyze_iron_core_diode_vs_frequency()

# Example of custom analysis
println("\n" * "="^60)
println("Custom frequency points analysis:")
custom_frequency_analysis([50.0, 500.0, 5000.0, 50000.0])

println("\nAnalysis complete! Plot saved as 'iron_core_diode_frequency_analysis.png'") 