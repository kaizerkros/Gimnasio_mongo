import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main


class ValidacionesTests(unittest.TestCase):
    def test_validar_email_gmail(self):
        self.assertEqual(main.validar_email('usuario@gmail.com'), 'usuario@gmail.com')

        with self.assertRaises(ValueError):
            main.validar_email('usuario@hotmail.com')

    def test_validar_telefono_formato_chileno(self):
        self.assertEqual(main.validar_telefono('+56 9 4444 5555'), '+56 9 4444 5555')

        with self.assertRaises(ValueError):
            main.validar_telefono('+56944445555')

        with self.assertRaises(ValueError):
            main.validar_telefono('+34 9 4444 5555')

    def test_validar_texto_obligatorio(self):
        self.assertEqual(main.validar_texto_obligatorio('Juan Perez', 'nombre'), 'Juan Perez')

        with self.assertRaises(ValueError):
            main.validar_texto_obligatorio('   ', 'nombre')


if __name__ == '__main__':
    unittest.main()
