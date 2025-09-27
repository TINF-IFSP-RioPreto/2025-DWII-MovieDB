## Formulários de autenticação e perfil de usuário

Estes são os principais formulários utilizados para autenticação e gerenciamento de perfil de usuário na aplicação.

- **RegistrationForm**
    - Descrição: Formulário para cadastro de novo usuário.
    - Campos:
      - `nome`: Nome do usuário.
      - `email`: Email do usuário.
      - `password`: Senha.
      - `password2`: Confirmação da senha.
      - `submit`: Botão para criar conta.


- **LoginForm**
    - Descrição: Formulário para autenticação de usuário.
    - Campos:
      - `email`: Email do usuário.
      - `password`: Senha.
      - `remember_me`: Permanecer conectado.
      - `submit`: Botão para login.


- **Read2FACodeForm**
    - Descrição: Formulário para leitura do código 2FA.
    - Campos:
        - `codigo`: Código fornecido pelo autenticador.
        - `submit`: Botão para enviar código.


- **SetNewPasswordForm**
    - Descrição: Formulário para cadastrar nova senha.
    - Campos:
      - `password`: Nova senha.
      - `password2`: Confirmação da nova senha.
      - `submit`: Botão para cadastrar nova senha.


- **AskToResetPasswordFor**m
    - Descrição: Formulário para solicitar redefinição de senha.
    - Campos:
      - `email`: Email para redefinir senha.
      - `submit`: Botão para redefinir senha.


- **ProfileForm**
    - Descrição: Formulário para edição do perfil do usuário autenticado.
    - Campos:
      - `id`: ID do usuário (oculto).
      - `nome`: Nome do usuário.
      - `email`: Email (imutável).
      - `usa_2fa`: Ativar segundo fator de autenticação.
      - `foto_raw`: Upload de foto de perfil.
      - `submit`: Botão para efetuar mudanças.
      - `remover_foto`: Botão para remover foto.
