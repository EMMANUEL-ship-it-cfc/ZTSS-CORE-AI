import java.util.Scanner;

public class ATMSystem {
    public static void main(String[] args) {
        Scanner input = new Scanner(System.in);

        // a) Display the ATM menu
        System.out.println("========================");
        System.out.println("ATM MENU");
        System.out.println("========================");
        System.out.println("1. Check Balance");
        System.out.println("2. Withdraw Cash");
        System.out.println("3. Deposit Money");
        System.out.println("4. Transfer Funds");
        System.out.println("5. Change PIN");
        System.out.println("6. Exit");
        System.out.println("7. Mini Statement");
        System.out.println("========================");

        // b) Prompt for and capture the choice
        System.out.print("Enter your option (1-7): ");
        int choice = input.nextInt();

        // c) Process the choice using a switch statement
        switch (choice) {
            case 1:
                System.out.println("Your current balance is KES 25,000.00");
                break;

            case 2:
                System.out.print("Enter amount to withdraw: ");
                double withdraw = input.nextDouble();
                System.out.println("Withdrawal of KES " + withdraw + " completed successfully.");
                break;

            case 3:
                System.out.print("Enter amount to deposit: ");
                double deposit = input.nextDouble();
                System.out.println("Deposit of KES " + deposit + " completed successfully.");
                break;

            case 4:
                System.out.print("Enter recipient account number: ");
                String account = input.next();
                System.out.print("Enter amount to transfer: ");
                double transfer = input.nextDouble();
                System.out.println("Transfer of KES " + transfer + " to account "
                        + account + " completed successfully.");
                break;

            case 5:
                System.out.print("Enter new PIN: ");
                String newPin = input.next();
                System.out.println("Your PIN has been changed successfully.");
                break;

            case 6:
                System.out.println("Thank you for banking with us. Goodbye!");
                break;

            case 7:
                System.out.println("Displaying your last 5 transactions...");
                break;

            default:
                System.out.println("Invalid option. Please select a number between 1 and 7.");
        }

        input.close();
    }
}