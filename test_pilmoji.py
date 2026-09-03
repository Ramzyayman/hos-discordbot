from card_generator import generate_shame_card
open('test_shame_v7.png', 'wb').write(generate_shame_card('Rams', '—FOOLS. HERETICS ????').getvalue())
