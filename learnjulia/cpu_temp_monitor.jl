# CPU Temperature Monitor
# visualization of 8 CPU core temperatures streamed by time


using Plots
using Statistics
using Random
using Dates

# structure to hold temperature data
mutable struct CPUTempData
    timestamps::Vector{Float64}
    core_temps::Matrix{Float64}  # 8 columns for cores, rows for time points
    max_points::Int
    current_index::Int
    
    function CPUTempData(max_points=1000)
        new(Float64[], zeros(Float64, 0, 8), max_points, 0)
    end
end

# add new temperature reading
function add_temperature_reading!(data::CPUTempData, timestamp::Float64, temps::Vector{Float64})
    if length(temps) != 8
        error("Expected 8 temperature readings, got $(length(temps))")
    end
    
    push!(data.timestamps, timestamp)
    data.core_temps = vcat(data.core_temps, reshape(temps, 1, 8))
    data.current_index += 1
    
    # keep only the most recent max_points readings
    if size(data.core_temps, 1) > data.max_points
        data.timestamps = data.timestamps[end-data.max_points+1:end]
        data.core_temps = data.core_temps[end-data.max_points+1:end, :]
        data.current_index = data.max_points
    end
end

# convert linear core index to 2D grid position (2x4 layout)
function core_to_position(core_index)
    # arrange 8 cores in 2x4 grid (2 rows, 4 columns)
    row = div(core_index - 1, 4) + 1
    col = mod(core_index - 1, 4) + 1
    return (row, col)
end

# create CPU heatmap from current average temperatures
function create_cpu_heatmap(data::CPUTempData)
    if size(data.core_temps, 1) == 0
        return plot(title="No Data Available")
    end
    
    # calculate average temperatures for each core
    avg_temps = mean(data.core_temps, dims=1)[1, :]
    
    # create 2x4 grid for CPU layout
    cpu_grid = zeros(2, 4)
    
    for (i, temp) in enumerate(avg_temps)
        row, col = core_to_position(i)
        cpu_grid[row, col] = temp
    end
    
    # create heatmap
    heatmap(cpu_grid, 
            title="CPU Core Temperature Heatmap (°C)",
            xlabel="CPU Column",
            ylabel="CPU Row", 
            color=:thermal,
            aspect_ratio=:equal,
            size=(400, 300),
            colorbar_title="Temperature (°C)")
    
    # add core labels
    for i in 1:8
        row, col = core_to_position(i)
        annotate!(col, row, text("Core $i\n$(round(avg_temps[i], digits=1))°C", 
                               :white, :center, 8))
    end
    
    return current()
end

# create time series plot of temperature progression
function create_temperature_timeseries(data::CPUTempData)
    if size(data.core_temps, 1) == 0
        return plot(title="No Data Available")
    end
    
    p = plot(title="CPU Core Temperatures Over Time",
             xlabel="Time (seconds)",
             ylabel="Temperature (°C)",
             legend=:outertopright,
             size=(800, 400))
    
    # plot each core's temperature over time
    colors = [:red, :blue, :green, :orange, :purple, :brown, :pink, :gray]
    
    for core in 1:8
        plot!(data.timestamps, data.core_temps[:, core],
              label="Core $core",
              linewidth=2,
              color=colors[core])
    end
    
    # add temperature zones
    hline!([70], color=:orange, linestyle=:dash, alpha=0.5, label="Warning (70°C)")
    hline!([85], color=:red, linestyle=:dash, alpha=0.5, label="Critical (85°C)")
    
    return p
end

# create combined visualization dashboard
function create_dashboard(data::CPUTempData)
    if size(data.core_temps, 1) == 0
        return plot(title="No Data Available")
    end
    
        # create individual plots
    heatmap_plot = create_cpu_heatmap(data)
    timeseries_plot = create_temperature_timeseries(data)
    
    # calculate statistics
    current_temps = data.core_temps[end, :]
    avg_temp = mean(current_temps)
    max_temp = maximum(current_temps)
    min_temp = minimum(current_temps)
    
    # create statistics text plot
    stats_text = """
    Current Statistics:
    Average: $(round(avg_temp, digits=1))°C
    Maximum: $(round(max_temp, digits=1))°C
    Minimum: $(round(min_temp, digits=1))°C
    Hot Cores: $(sum(current_temps .> 70))
    Critical: $(sum(current_temps .> 85))
    """
    
    stats_plot = plot([], [], showaxis=false, grid=false, 
                     title="Temperature Statistics",
                     size=(300, 300))
    annotate!(0.5, 0.5, text(stats_text, :left, 12))
    xlims!(0, 1)
    ylims!(0, 1)
    
    # combine all plots
    combined_plot = plot(heatmap_plot, stats_plot, timeseries_plot,
                        layout=@layout([a b; c{0.6h}]),
                        size=(1200, 800))
    
    return combined_plot
end

# generate sample streaming data (for demonstration)
function generate_sample_data()
    # base temperatures for each core (simulating different workloads)
    base_temps = [45.0, 42.0, 48.0, 44.0, 46.0, 43.0, 47.0, 45.0]
    
    # generate random temperature variations
    temp_variations = randn(8) * 5.0  # random variations up to ±5°C
    current_temps = base_temps .+ temp_variations
    
    # ensure temperatures are realistic (30-90°C range)
    current_temps = clamp.(current_temps, 30.0, 90.0)
    
    return current_temps
end

# main monitoring function
function monitor_cpu_temperatures(duration_seconds=60, update_interval=1.0)
    println("Starting CPU Temperature Monitor...")
    println("Monitoring for $(duration_seconds) seconds with $(update_interval)s intervals")
    println("Press Ctrl+C to stop early")
    
    data = CPUTempData(1000)  # store up to 1000 data points
    start_time = time()
    
    try
        while time() - start_time < duration_seconds
            # get current timestamp (relative to start)
            current_time = time() - start_time
            
            # in a real implementation, you would read from actual sensors here
            # For demonstration, we generate sample data
            current_temps = generate_sample_data()
            
            # add data point
            add_temperature_reading!(data, current_time, current_temps)
            
            # create and display dashboard
            dashboard = create_dashboard(data)
            display(dashboard)
            
            # print current status
            avg_temp = mean(current_temps)
            max_temp = maximum(current_temps)
            hot_cores = sum(current_temps .> 70)
            critical_cores = sum(current_temps .> 85)
            
            println("Time: $(round(current_time, digits=1))s | " *
                   "Avg: $(round(avg_temp, digits=1))°C | " *
                   "Max: $(round(max_temp, digits=1))°C | " *
                   "Hot: $hot_cores | Critical: $critical_cores")
            
                # check for critical temperatures
            if critical_cores > 0
                println("⚠️  CRITICAL: $(critical_cores) cores above 85°C!")
            elseif hot_cores > 0
                println("⚠️  WARNING: $(hot_cores) cores above 70°C")
            end
            
            sleep(update_interval)
        end
        
    catch InterruptException
        println("\nMonitoring stopped by user")
    end
    
    # save final dashboard
    final_dashboard = create_dashboard(data)
    savefig(final_dashboard, "cpu_temperature_monitor.png")
    println("Final dashboard saved as 'cpu_temperature_monitor.png'")
    
    return data
end

# function to load temperature data from file (CSV format)
function load_temperature_data(filename::String)
    println("Loading temperature data from $filename...")
    
    data = CPUTempData()
    
    try
        lines = readlines(filename)
        
        for (i, line) in enumerate(lines)
            if i == 1 && startswith(line, "time")  # Skip header
                continue
            end
            
            parts = split(line, ',')
            if length(parts) >= 9  # time + 8 temperatures
                timestamp = parse(Float64, parts[1])
                temps = [parse(Float64, parts[j]) for j in 2:9]
                add_temperature_reading!(data, timestamp, temps)
            end
        end
        
        println("Loaded $(size(data.core_temps, 1)) temperature readings")
        
    catch e
        println("Error loading data: $e")
        println("Expected CSV format: time,core1,core2,core3,core4,core5,core6,core7,core8")
    end
    
    return data
end

# interactive menu system
function main_menu()
    println("\n" * "="^60)
    println("CPU Temperature Monitor")
    println("="^60)
    println("1. Start real-time monitoring (demo with simulated data)")
    println("2. Load temperature data from CSV file")
    println("3. Generate sample data and display dashboard") 
    println("4. Exit")
    println("="^60)
    
    while true
        print("Select option (1-4): ")
        choice = strip(readline())
        
        if choice == "1"
            print("Enter monitoring duration (seconds, default 60): ")
            duration_input = strip(readline())
            duration = isempty(duration_input) ? 60 : parse(Float64, duration_input)
            
            print("Enter update interval (seconds, default 1.0): ")
            interval_input = strip(readline())
            interval = isempty(interval_input) ? 1.0 : parse(Float64, interval_input)
            
            monitor_cpu_temperatures(duration, interval)
            break
            
        elseif choice == "2"
            print("Enter CSV filename: ")
            filename = strip(readline())
            
            if isfile(filename)
                data = load_temperature_data(filename)
                dashboard = create_dashboard(data)
                display(dashboard)
                savefig(dashboard, "loaded_temperature_dashboard.png")
                println("Dashboard saved as 'loaded_temperature_dashboard.png'")
            else
                println("File not found: $filename")
            end
            break
            
        elseif choice == "3"
            # generate sample dataset
            data = CPUTempData()
            start_time = 0.0
            
            # generate 60 seconds of sample data
            for t in 0:1:60
                temps = generate_sample_data()
                add_temperature_reading!(data, Float64(t), temps)
            end
            
            dashboard = create_dashboard(data)
            display(dashboard)
            savefig(dashboard, "sample_temperature_dashboard.png")
            println("Sample dashboard saved as 'sample_temperature_dashboard.png'")
            break
            
        elseif choice == "4"
            println("Goodbye!")
            break
            
        else
            println("Invalid choice. Please select 1-4.")
        end
    end
end

# run the program
if abspath(PROGRAM_FILE) == abspath(@__FILE__)
    main_menu()
end 