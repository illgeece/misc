#Random number guessing game
#Generate random number, prompt user for input
# and then check if it is correct - incorrect answer can retry 10 times
#Tracks attempts and displays accuracy measure


using Random

function play_number_guessing_game()
#random number gen
    secret_number = rand(1:100)
    attempts = 0
    max_attempts = 10

    println("Welcome to the Number Guessing Game!")
    println("I'm thinking of a number between 1 and 100.")
    println("You have $max_attempts attempts to guess it.")

    while attempts < max_attempts
        print("\nEnter your guess: ")
        
#user input
        try
            guess = parse(Int, readline())
            
            if guess < 1 || guess > 100
                println("Please enter a number between 1 and 100.")
                continue
            end

            attempts += 1

            if guess < secret_number
                println("Too low! Try a higher number.")
            elseif guess > secret_number
                println("Too high! Try a lower number.")
            else
                println("\nCongratulations! You guessed the number in $attempts attempts!")
                return
            end
#reprompt and check num
            println("Attempts remaining: $(max_attempts - attempts)")

        catch e
            println("Invalid input! Please enter a valid number.")
        end
    end

    println("\nGame Over! The number was $secret_number.")
end

play_number_guessing_game() 