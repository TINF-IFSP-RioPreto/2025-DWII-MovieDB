## Rotas da Blueprint

As principais rotas implementadas na *blueprint* de autenticação são:

- **auth.register**
    - Rota: `/auth/register`
    - Argumentos: nenhum
    - Descrição: Exibe o formulário de registro de usuário e processa o cadastro. Envia email de
      confirmação.

- **auth.revalida_email**
    - Rota: `/auth/revalida_email/<uuid:user_id>`
    - Argumentos: `user_id`
    - Descrição: Reenvia o email de validação para o usuário com o ID fornecido.

- **auth.login**
    - Rota: `/auth/login`
    - Argumentos: nenhum
    - Descrição: Exibe o formulário de login e processa a autenticação do usuário.

- **auth.get2fa**
    - Rota: `/auth/get2fa`
    - Argumentos: nenhum
    - Descrição: Exibe e processa o formulário de segundo fator de autenticação (2FA).

- **auth.logout**
    - Rota: `/auth/logout`
    - Argumentos: nenhum
    - Descrição: Realiza o logout do usuário autenticado.

- **auth.valida_email**
    - Rota: `/auth/valida_email/<token>`
    - Argumentos: `token`
    - Descrição: Valida o email do usuário a partir de um token JWT enviado na URL.

- **auth.reset_password**
    - Rota: `/auth/reset_password/<token>`
    - Argumentos: `token`
    - Descrição: Exibe o formulário para redefinição de senha e processa a troca de senha do
      usuário.

- **auth.new_password**
    - Rota: `/auth/new_password`
    - Argumentos: nenhum
    - Descrição: Exibe o formulário para solicitar redefinição de senha.

- **auth.imagem**
    - Rota: `/auth/<uuid:id_usuario>/imagem/<size>`
    - Argumentos: `id_usuario`, `size`
    - Descrição: Retorna a imagem ou avatar do usuário autenticado, conforme o parâmetro size.

- **auth.profile**
    - Rotas: `/auth/`, `/auth/profile`
    - Argumentos: nenhum
    - Descrição: Exibe e processa o formulário de edição do perfil do usuário autenticado.

- **auth.enable_2fa**
    - Rota: `/auth/enable_2fa`
    - Argumentos: nenhum
    - Descrição: Ativa o segundo fator de autenticação (2FA) para o usuário autenticado.
