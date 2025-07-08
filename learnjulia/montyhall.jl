using Random

function monty_hall_simulation(num_trials::Int = 1000)
    switch_wins = 0
    stay_wins = 0
    
    for _ in 1:num_trials
        # Set up doors (1 car, 2 goats)
        doors = [1, 2, 3]
        car = rand(doors)
        
        # Player's initial choice
        initial_choice = rand(doors)
        
        # Monty opens a door
        remaining_doors = filter(d -> d != initial_choice && d != car, doors)
        monty_opens = rand(remaining_doors)
        
        # If player switches
        switch_doors = filter(d -> d != initial_choice && d != monty_opens, doors)[1]
        if switch_doors == car
            switch_wins += 1
        end
        
        # If player stays
        if initial_choice == car
            stay_wins += 1
        end
    end
    
    # Calculate probabilities
    switch_prob = switch_wins / num_trials
    stay_prob = stay_wins / num_trials
    
    println("\nMonty Hall Simulation Results ($num_trials trials):")
    println("Probability of winning by switching: $(round(switch_prob * 100, digits=1))%")
    println("Probability of winning by staying: $(round(stay_prob * 100, digits=1))%")
end

# Run simulation
monty_hall_simulation()
