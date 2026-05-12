# 📚 Tutorial: Como Subir Mudanças para o GitHub

## ✅ Sua Configuração (JÁ PRONTA)
Seu repositório já está configurado e vinculado ao GitHub. Você só precisa fazer 3 passos simples:

---

## 🚀 Passo 1: Verificar o Status das Mudanças
Abra o terminal PowerShell e execute:

```powershell
git status
```

**O que você verá:**
- Arquivos modificados (em vermelho)
- Arquivos novos (em vermelho)

---

## 📝 Passo 2: Adicionar as Mudanças

### Opção A: Adicionar TUDO
```powershell
git add -A
```

### Opção B: Adicionar Arquivos Específicos
```powershell
git add app/routes.py app/models.py
```

---

## 💾 Passo 3: Fazer o Commit

```powershell
git commit -m "Descrição breve das mudanças"
```

**Exemplos de boas mensagens:**
```powershell
git commit -m "Fix: Corrigir erro de planos e turmas"
git commit -m "Feature: Adicionar novo relatório de pagamentos"
git commit -m "Refactor: Melhorar código de validação"
git commit -m "Docs: Atualizar README com instruções"
```

---

## 🌐 Passo 4: Enviar para o GitHub

```powershell
git push origin main
```

Se pedir para fazer login, use suas credenciais do GitHub.

---

## ⚡ ATALHO RÁPIDO (3 Comandos em 1)

Se você não fez nenhum commit ainda e quer fazer tudo de uma vez:

```powershell
git add -A ; git commit -m "Descrição da mudança" ; git push origin main
```

---

## 📋 Checklist Rápido (Sempre Antes de Push)

1. ✅ Fez as mudanças no código
2. ✅ Testou localmente (rodou a aplicação)
3. ✅ Executou `git add -A`
4. ✅ Executou `git commit -m "mensagem"`
5. ✅ Executou `git push origin main`

---

## ❌ Se Der Erro: "Your branch is ahead by X commits"

**Problema:** Você fez commits mas esqueceu de fazer push

**Solução:**
```powershell
git push origin main
```

---

## ❌ Se Der Erro: "Permission denied" ou Autenticação

**Solução 1: Usar Token (Recomendado)**
1. Vá em GitHub → Settings → Developer settings → Personal access tokens
2. Crie um novo token com permissão `repo`
3. Quando pedir senha, use o token no lugar da senha

**Solução 2: Configurar SSH**
Entre em contato se precisar configurar SSH.

---

## 🔍 Ver Histórico de Commits

```powershell
git log --oneline
```

Para ver quantos commits você fez:
```powershell
git log --oneline | wc -l
```

---

## 📊 Ver o Que Você Enviou para o GitHub

Acesse: https://github.com/Carlosvictoor/ctcaranha

---

## 💡 Dicas Importantes

### ❌ NÃO fazer commit de:
- `.venv/` (ambiente virtual)
- `__pycache__/`
- `.env` (variáveis sensíveis)
- `instance/` (banco de dados local)

Essas pastas já estão em `.gitignore`, então está tudo bem.

### ✅ Fazer commit de:
- `app/` (código)
- `templates/` (HTML)
- `static/` (CSS, JS)
- `requirements.txt` (dependências)
- `README.md` (documentação)

---

## 🎯 Fluxo Básico do Seu Dia

```
1. Faz mudanças no código
   ↓
2. Testa localmente
   ↓
3. git add -A
   ↓
4. git commit -m "descrição"
   ↓
5. git push origin main
   ↓
6. ✅ Mudanças no GitHub!
```

---

## 📞 Precisa de Ajuda?

Se der erro, tente:

1. **Ver o status atual:**
   ```powershell
   git status
   ```

2. **Ver o erro completo:**
   ```powershell
   git push origin main -v
   ```

3. **Desfazer último commit (antes de push):**
   ```powershell
   git reset --soft HEAD~1
   ```

---

**Pronto! Agora você não precisa pedir ajuda toda hora.** 🎉

Qualquer dúvida é só rodar os comandos e ver a saída.
