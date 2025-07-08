#monty hall problem from before improved with simulation
#plot probability of winning for each trial and compile in plot
# add theoretical lines for switching and staying


using Random
using Plots

function monty_hall_simulation(num_trials::Int = 1000)
    switch_wins = 0
    stay_wins = 0
    
    # arrays to store probabilities over time
    switch_probs = Float64[]
    stay_probs = Float64[]
    trial_numbers = Int[]
    
    for trial in 1:num_trials
        # set up doors (1 car, 2 goats)
        doors = [1, 2, 3]
        car = rand(doors)
        
        # player's initial choice
        initial_choice = rand(doors)
        
        # 1st open
        remaining_doors = filter(d -> d != initial_choice && d != car, doors)
        monty_opens = rand(remaining_doors)
        
        # player switch?
        switch_doors = filter(d -> d != initial_choice && d != monty_opens, doors)[1]
        if switch_doors == car
            switch_wins += 1
        end
        
        # if player stays
        if initial_choice == car
            stay_wins += 1
        end
        
        # calculate and store probabilities
        push!(switch_probs, switch_wins / trial)
        push!(stay_probs, stay_wins / trial)
        push!(trial_numbers, trial)
    end
    
    # calculate final probabilities
    switch_prob = switch_wins / num_trials
    stay_prob = stay_wins / num_trials
    
    # create the plot
    p = plot(trial_numbers, [switch_probs, stay_probs],
             label=["Switching" "Staying"],
             xlabel="Number of Trials",
             ylabel="Probability of Winning",
             title="Monty Hall Problem: Probability Convergence",
             linewidth=2,
             ylims=(0, 1),
             legend=:bottomright)
    
    # theoretical lines
    hline!([2/3], label="Theoretical Switch (2/3)", linestyle=:dash, color=:red)
    hline!([1/3], label="Theoretical Stay (1/3)", linestyle=:dash, color=:blue)
    
    # display results
    println("\nMonty Hall Simulation Results ($num_trials trials):")
    println("Probability of winning by switching: $(round(switch_prob * 100, digits=1))%")
    println("Probability of winning by staying: $(round(stay_prob * 100, digits=1))%")
    
    # save and display
    savefig(p, "monty_hall_simulation.png")
    display(p)
end

# run simulation with 1000 trials
monty_hall_simulation(1000) 