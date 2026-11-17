"""Testes do núcleo (mdtech/): nomes, diâmetro, preço, fotos e leitura da base.
Rodar na raiz do repositório:  python -m unittest discover -s tests -t ."""
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from mdtech import base, config, fotos, textos as T


class TesteTextos(unittest.TestCase):
    def test_nome_produto_corta_nas_specs(self):
        self.assertEqual(T.nome_produto("PINÇA DE APREENSÃO GOLFINHO MDTECH D=5MM C=330MM"), "Pinça de Apreensão Golfinho")

    def test_nome_produto_mdtech_no_meio_nao_engole_o_resto(self):
        self.assertEqual(T.nome_produto("CAMISA MDTECH PARA CISTOURETROSCOPIA D=16,5FR"), "Camisa para Cistouretroscopia")

    def test_nome_produto_vazio(self):
        self.assertEqual(T.nome_produto(""), "")
        self.assertEqual(T.nome_produto(None), "")

    def test_diametro_mm_fr_e_vazio(self):
        self.assertEqual(T.diametro_fmt({"diametro": "5"}), "5 mm")
        self.assertEqual(T.diametro_fmt({"diametro_fr": "16,5"}), "16,5 Fr")
        self.assertEqual(T.diametro_fmt({"diametro": "5", "diametro_fr": "16"}), "5 mm")   # mm tem prioridade
        self.assertEqual(T.diametro_fmt({}), "")

    def test_preco(self):
        self.assertEqual(T.preco_num({"preco": "1.250,50"}), 1250.5)
        self.assertEqual(T.preco_num({"preco": 1250}), 1250.0)
        self.assertIsNone(T.preco_num({"preco": ""}))
        self.assertIsNone(T.preco_num({"preco": "0"}))
        self.assertEqual(T.brl(1250), "R$ 1.250,00")
        self.assertEqual(T.brl(None), "")

    def test_eh_sim(self):
        self.assertTrue(T.eh_sim("Sim"))
        self.assertFalse(T.eh_sim("Não"))


class TesteFotos(unittest.TestCase):
    def test_matcher_tolerante(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / "TONGLU").mkdir()
            (pasta / "TONGLU" / "a153.jpg").write_bytes(b"x")
            (pasta / "solta_1.png").write_bytes(b"x")
            self.assertEqual(fotos.buscar("A153.C", pasta).name, "a153.jpg")   # caixa e sufixo .C
            self.assertEqual(fotos.buscar("A153", pasta).name, "a153.jpg")
            self.assertEqual(fotos.subpasta("A153", pasta), "TONGLU")
            self.assertEqual(fotos.subpasta("solta1", pasta), "(raiz)")        # ignora "_"
            self.assertIsNone(fotos.buscar("ZZZ", pasta))


class TesteBase(unittest.TestCase):
    def test_colunas_obrigatorias_na_base_real(self):
        itens = base.carregar()
        self.assertGreater(len(itens), 100)
        for chave in ("codigo", "descricao", "especialidade", "familia", "marca", "anvisa", "ncm", "diametro", "diametro_fr"):
            self.assertIn(chave, itens[0], f"coluna '{base.COLUNAS.get(chave)}' sumiu da planilha")
        self.assertTrue(all(i["codigo"] for i in itens))

    def test_especialidades_conhecidas(self):
        esp = {i["especialidade"] for i in base.carregar()}
        self.assertEqual(esp, {"Laparoscopia", "Urologia", "Histeroscopia"})

    def test_cabecalho_sem_codigo_da_erro_claro(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "x.xlsx"
            wb = Workbook(); ws = wb.active; ws.title = config.BASE_ABA
            ws.append(["Nada", "Útil"]); wb.save(caminho)
            with self.assertRaises(ValueError):
                base.carregar(caminho)

    def test_linhas_modelo_e_sem_codigo_sao_ignoradas(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "x.xlsx"
            wb = Workbook(); ws = wb.active; ws.title = config.BASE_ABA
            ws.append([base.COLUNAS["codigo"], base.COLUNAS["marca"]])
            ws.append(["A1", "TONGLU"]); ws.append(["", "TONGLU"]); ws.append(["A2", "Exemplo"]); ws.append(["— modelo", "X"])
            wb.save(caminho)
            self.assertEqual([i["codigo"] for i in base.carregar(caminho)], ["A1"])


if __name__ == "__main__":
    unittest.main()
