from aerona.services.books.history import ending_line


def test_an_ending_names_its_epoch_once() -> None:
    assert ending_line("dead", 6, "Epoch 6: the uprising died out.") == "Dead in Epoch 6: the uprising died out."
    assert ending_line("dead", 6, "Epoch 6, world year 290: died at age 40.") == "Dead in Epoch 6: died at age 40."
    assert ending_line("dead", 6, "Epoch 4: fled. Epoch 6: fell.") == "Dead in Epoch 6: Epoch 4: fled. Epoch 6: fell."
    assert ending_line("destroyed", 8, None) == "Destroyed in Epoch 8"
