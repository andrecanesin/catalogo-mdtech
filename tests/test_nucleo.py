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

    def test_nome_endoscopio_sem_spec(self):
        self.assertEqual(T.nome_produto("ENDOSCÓPIO RÍGIDO MDTECH AV=30°, D=4MM, C=302MM, AUTOCLAVÁVEL (134°). TECNOLOGIA AVANÇADA"),
                         "Endoscópio Rígido")
        self.assertEqual(T.nome_produto("ENDOSCÓPIO RÍGIDO 4K HIGH DEFINITION MDTECH AV=12°, D=4MM"), "Endoscópio Rígido 4K High Definition")

    def test_nome_mantem_a_medida_que_diferencia_o_item(self):
        self.assertEqual(T.nome_produto("CLAMP TIPO BULLDOG 25MM CURVO MDTECH AUTOCLAVAVEL (134°)"), "Clamp tipo Bulldog 25 mm Curvo")
        self.assertEqual(T.nome_produto("AGULHA DE PUNÇAO 1.8MM MDTECH D=5 C=330MM"), "Agulha de Punçao 1,8 mm")

    def test_nome_com_parenteses_de_spec(self):
        self.assertEqual(T.nome_produto("CONJUNTO DE TUBOS MDTECH VÁLVULA TIPO PISTÃO (D=10MM) E (D=5MM)"), "Conjunto de Tubos Válvula tipo Pistão")

    def test_grafia_unica_trocarte(self):
        self.assertEqual(T.nome_produto("TROCARTER COM VALVULA MULTIFUNCIONAL MDTECH D=5.5MM"), "Trocarte com Valvula Multifuncional")
        self.assertEqual(T.nome_produto("TROCATER DE PONTA PROTEGIDA MDTECH D=5MM"), "Trocarte de Ponta Protegida")

    def test_nome_produto_vazio(self):
        self.assertEqual(T.nome_produto(""), "")
        self.assertEqual(T.nome_produto(None), "")

    def test_diametro_mm_fr_e_vazio(self):
        self.assertEqual(T.diametro_fmt({"diametro": "5"}), "5 mm")
        self.assertEqual(T.diametro_fmt({"diametro_fr": "16,5"}), "16,5 Fr")
        self.assertEqual(T.diametro_fmt({"diametro": "5", "diametro_fr": "16"}), "5 mm")   # mm tem prioridade
        self.assertEqual(T.diametro_fmt({}), "")
        self.assertEqual(T.diametro_fmt({"diametro": "2.9"}), "2,9 mm")                    # vírgula brasileira
        self.assertEqual(T.diametro_fmt({"diametro_fr": "16.5"}), "16,5 Fr")

    def test_ncm_num_formato_so(self):
        self.assertEqual(T.ncm_fmt("90183999"), "9018.39.99")
        self.assertEqual(T.ncm_fmt("9018.90.99"), "9018.90.99")
        self.assertEqual(T.ncm_fmt(""), "")

    def test_otica_e_uso_unico(self):
        self.assertTrue(T.eh_otica({"descricao": "ENDOSCÓPIO RÍGIDO MDTECH AV=30°"}))
        self.assertFalse(T.eh_otica({"descricao": "CABO DE FIBRA ÓTICA COM CONECTOR"}))
        self.assertFalse(T.eh_otica({"descricao": "ELETRODO MONOPOLAR TIPO LOOP 30° MDTECH"}))
        self.assertTrue(T.uso_unico({"descricao": "CLIPS DE TITANIO TAMANHO S COR BRANCO MDTECH"}))
        self.assertFalse(T.uso_unico({"descricao": "PINÇA DE APREENSÃO MDTECH"}))

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

    def test_base_sem_grafias_antigas_de_trocarte(self):
        for i in base.carregar():
            for campo in ("descricao", "familia"):
                self.assertNotRegex(i[campo], r"(?i)troc(ater|arter)", f"{i['codigo']}: {campo}")

    def test_nenhum_card_identico_na_base(self):
        """Dois produtos da mesma especialidade com nome e medidas iguais seriam cards indistinguíveis."""
        vistos = {}
        for i in base.carregar():
            chave = (i["especialidade"], T.nome_produto(i["descricao"]), T.diametro_fmt(i), i["comprimento"], i["angulo"])
            if chave in vistos and vistos[chave] != i["codigo"]:
                self.fail(f"cards idênticos: {vistos[chave]} e {i['codigo']} ({chave[1]})")
            vistos[chave] = i["codigo"]

    def test_ncm_da_base_vira_formato_unico(self):
        for i in base.carregar():
            if i["ncm"]:
                self.assertRegex(T.ncm_fmt(i["ncm"]), r"^\d{4}\.\d{2}\.\d{2}$", i["codigo"])

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
