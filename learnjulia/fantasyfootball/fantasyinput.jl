# Julia input parser for statistics file
# parses groups of statistics with labeled categories and calculates mean and median, returns a dictionary with category names as keys and statistics as values

using Statistics

function parse_stats_file(filename::String)
    results = Dict{String, Dict{String, Float64}}()
    try
        open(filename, "r") do file
            for line in eachline(file)
                # skip empty lines
                if isempty(strip(line))
                    continue
                end
                # parse each line (category:values)
                if contains(line, ":")
                    parts = split(line, ":", limit=2)
                    if length(parts) == 2
                        category = strip(parts[1])
                        values_str = strip(parts[2])
                        
                        # parse comma-separated values
                        value_strings = split(values_str, ",")
                        values = Float64[]
                        
                        for val_str in value_strings
                            val_str = strip(val_str)
                            if !isempty(val_str)
                                try
                                    push!(values, parse(Float64, val_str))
                                catch e
                                    println("Warning: Could not parse value '$val_str' in category '$category'")
                                end
                            end
                        end
                        # calculate statistics if we have values
                        if !isempty(values)
                            stats = Dict{String, Float64}()
                            stats["mean"] = mean(values)
                            stats["median"] = median(values)
                            stats["count"] = length(values)
                            
                            results[category] = stats
                            
                            println("Category: $category")
                            println("  Values: $(length(values)) data points")
                            println("  Mean: $(round(stats["mean"], digits=2))")
                            println("  Median: $(round(stats["median"], digits=2))")
                            println()
                        else
                            println("Warning: No valid values found for category '$category'")
                        end
                    end
                end
            end
        end
    catch e
        println("Error reading file '$filename': $e")
        return nothing
    end
    return results
end
#from a string instead of a file, useable for functions to be implemented later
function parse_stats_string(input::String)

    results = Dict{String, Dict{String, Float64}}()
    for line in split(input, "\n")
        # skip empty lines
        if isempty(strip(line))
            continue
        end
        # parse each line (category:values)
        if contains(line, ":")
            parts = split(line, ":", limit=2)
            if length(parts) == 2
                category = strip(parts[1])
                values_str = strip(parts[2])
                # parse comma-separated values
                value_strings = split(values_str, ",")
                values = Float64[]
                for val_str in value_strings
                    val_str = strip(val_str)
                    if !isempty(val_str)
                        try
                            push!(values, parse(Float64, val_str))
                        catch e
                            println("Warning: Could not parse value '$val_str' in category '$category'")
                        end
                    end
                end
                # calculate statistics if we have values
                if !isempty(values)
                    stats = Dict{String, Float64}()
                    stats["mean"] = mean(values)
                    stats["median"] = median(values)
                    stats["count"] = length(values)
                    results[category] = stats
                    println("Category: $category")
                    println("  Values: $(length(values)) data points")
                    println("  Mean: $(round(stats["mean"], digits=2))")
                    println("  Median: $(round(stats["median"], digits=2))")
                    println()
                else
                    println("Warning: No valid values found for category '$category'")
                end
            end
        end
    end
    return results
end



