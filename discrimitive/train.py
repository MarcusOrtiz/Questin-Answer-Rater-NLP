import torch.nn as nn
import torch.optim as optim
import torch
from .load_datasets import load_datasets
from torch.nn.utils.rnn import pad_sequence
from .qa import create_model
from torch.utils.data import Dataset, DataLoader

# TRAIN_DATA_NAME = 'train_marcus.json'
# VAL_DATA_NAME = 'train_marcus.json'
# TEST_DATA_NAME = 'train_marcus.json'
TRAIN_DATA_NAME = 'train_formatted_output_w_comma.json'
VAL_DATA_NAME = 'valid_formatted_output_w_comma.json'
TEST_DATA_NAME = 'test_formatted_output_w_comma.json'

BATCH_SIZE = 10
SHUFFLE = True
EPOCHS = 20
LEARNING_RATE = 0.001
PATIENCE = 10


def collate_batch(batch):
    questions, answers, scores = zip(*batch)

    # Pad questions and answers to have the same length within each batch
    questions_padded = pad_sequence(questions, batch_first=True, padding_value=0)  # Assuming 0 is your padding index
    answers_padded = pad_sequence(answers, batch_first=True, padding_value=0)
    scores = torch.tensor(scores, dtype=torch.float)

    return questions_padded, answers_padded, scores


def train():
    train_data, val_data, test_data, vocab = load_datasets(TRAIN_DATA_NAME, VAL_DATA_NAME, TEST_DATA_NAME)

    model = create_model(len(vocab))

    qa_train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=SHUFFLE, collate_fn=collate_batch)
    qa_val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=SHUFFLE, collate_fn=collate_batch)

    # Define the loss function and optimizer
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.MSELoss()

    best_val_loss = float('inf')
    epochs_no_improve = 0
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0
        for questions, answers, scores in qa_train_loader:
            # Forward pass
            predictions = model(questions, answers).squeeze()
            # print(f'train predictions: {predictions}')
            # print(f'train scores: {scores}')
            # Compute the loss
            loss = loss_fn(predictions, scores)

            # Backward pass and optimization
            optimizer.zero_grad()  # Clear existing gradients
            loss.backward()  # Backpropagation
            optimizer.step()  # Update weights
            train_loss += loss.item()

        train_loss = train_loss / len(qa_train_loader)

        model.eval()
        val_accuracy = 0
        val_loss = 0
        total_scores = 0
        with torch.no_grad():
            printCount = 10
            for questions, answers, scores in qa_val_loader:
                predictions = model(questions, answers).squeeze()
                # print(f'val predictions: {predictions}')
                # print(f'val scores: {scores}')
                loss = loss_fn(predictions, scores)
                val_loss += loss.item()

                # accuracy
                diff = torch.abs(predictions - scores)
                accurate = torch.where(diff < 0.5, torch.ones_like(diff), torch.zeros_like(diff))
                val_accuracy += torch.sum(accurate).item()
                total_scores += len(scores)
                if printCount > 0:
                    print(f'val predictions: {predictions}')
                    print(f'val scores: {scores}')
                    print(f'val diff: {diff}')
                    print(f'val accurate: {accurate}')
                    print(f'val accuracy: {val_accuracy}')
                    print(f'val total_scores: {total_scores}')
                    printCount -= 1

        val_loss = val_loss / len(qa_val_loader)
        val_accuracy = val_accuracy / total_scores

        # Print statistics
        print(f"Epoch {epoch},"
              f"Training Loss: {train_loss}, Validation Loss: {val_loss}, "
              f"Val Accuracy: {val_accuracy}")

        # Early Stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            # Save the model if it's the best so far
            torch.save(model.state_dict(), 'best_model.pth')
        else:
            epochs_no_improve += 1

        if epochs_no_improve == PATIENCE:
            print(f'Early stopping! Epoch: {epoch}')
            break

    torch.save(model.state_dict(), 'model_ending_1.pth')


if __name__ == '__main__':
    train()
