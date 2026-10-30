# GoatLLM — Brief de développement pour Codex

> **Rôle :** tu es l'ingénieur logiciel principal chargé de construire **GoatLLM**, application Discord open source auto-hébergée, légère et maintenable, destinée à l'organisation GitHub [`GoatsSoftware`](https://github.com/GoatsSoftware). Tu travailles dans le dossier courant, réservé au projet. **Construis le code et les fichiers, ne te contente pas d'expliquer comment faire.**
>
> **Priorité :** une excellente **Milestone 1 (M1) text-only**. Nous pourrons y consacrer plusieurs soirées. Ne bâcle pas l'architecture, mais refuse la complexité qui n'apporte rien à cette première version.

## 1. Produit et contexte

GoatLLM permet à un groupe d'amis d'appeler un LLM depuis une **conversation privée de groupe Discord (group DM)**, **sans créer de serveur Discord**, via une commande `/ask` (ou autre configurable) d'une **application Discord installable sur le compte utilisateur (User Install)**. Il doit également pouvoir fonctionner dans d'autres contextes autorisés par Discord, sans que cela compromette la compatibilité group DM.

**Architecture d'exploitation :** **une seule instance GoatLLM active, hébergée sur le PC d'un ami**, reçoit les interactions Discord ; **une seule instance Ollama sur ce même PC** fournit le modèle. Tous les amis autorisés peuvent utiliser la même application depuis Discord ; ils n'ont rien à installer localement pour l'utiliser. Les utilisateurs peuvent devoir installer/autoriser l'application sur leur compte Discord selon la configuration d'installation choisie. **Ne jamais affirmer qu'un bot classique peut être ajouté comme membre d'un group DM : ce n'est pas le mécanisme utilisé.**

Les contributeurs qui clonent le dépôt peuvent lancer **leur propre instance**, idéalement avec **leur propre application Discord et leur propre token** pour éviter les instances concurrentes utilisant le même token. Pas d'exécutable ni d'interface graphique à développer en M1, mais conserver un point d'entrée CLI propre pour un éventuel packaging futur.

## 2. Critères non négociables de la M1

1. Application Discord officielle, avec **`USER_INSTALL`** et contexte **`PRIVATE_CHANNEL`** pour `/ask`. Confirmer dans la version installée de `discord.py` la syntaxe des décorateurs `app_commands` (par exemple `allowed_installs` / `allowed_contexts`), et ne pas inventer d'API. Prévoir aussi l'usage en `BOT_DM`/`GUILD` **si** possible sans devoir inviter un bot dans un serveur, mais `PRIVATE_CHANNEL` est obligatoire.
2. `/ask prompt:<texte>` : reçoit le texte, contacte un LLM via **Ollama local** (HTTP), puis renvoie la réponse **visible dans la conversation**, non éphémère lorsque Discord l'autorise. **Aucune lecture passive de la conversation**, pas de collecte des autres messages, pas de message-content intent non nécessaire, pas de self-bot ni de token utilisateur.
3. **Réponse différée immédiatement** (`defer`) afin de respecter le délai initial Discord (~3 s). Répondre via édition/follow-up dans la fenêtre autorisée (~15 min) ; appliquer un timeout inférieur et traiter les dépassements. Une erreur LLM ne doit pas tuer le processus.
4. **Aucun historique persistant** des prompts, réponses ou conversations. M1 **stateless** : seul le prompt courant, plus un system prompt configurable, est envoyé au LLM. Pas de SQLite ni d'archivage de messages. Logs sobres sans contenu des prompts, réponses, secrets, ni identifiants personnels par défaut.
5. **Une instance pour plusieurs utilisateurs** : pas de dépendance à un `user_id` hardcodé. Ajouter une **liste d'IDs Discord autorisés configurable**, activée par défaut en mode privé ou une autre stratégie sûre, documentée et simple. Attention : un utilisateur autorisé peut lancer une requête dans une conversation où d'autres verront la réponse ; expliquer ce comportement dans la doc. Ne pas se fier à un simple nom d'utilisateur.
6. **Portabilité matérielle** : aucun modèle gravé dans le code. Support Ollama sur Windows/Linux, RTX 3070 8 Go, RTX 3050 Ti Laptop 4 Go ou CPU ; recommander des tailles de modèles plutôt que promettre des performances. L'utilisateur installe lui-même Ollama et télécharge un modèle compatible avec sa mémoire.
7. **Sobriété** : aucun polling superflu, pas de gros framework d'agents, pas de processus GPU propre à GoatLLM, pas de préchargement obligatoire. Limite de requêtes simultanées (défaut : une génération), timeout, taille maximale du prompt, plafond de tokens générés, contexte Ollama borné et durée `keep_alive` configurable (par défaut faible ou `0`, avec explication du compromis latence/VRAM). Éviter de retenir un modèle chargé inutilement.
8. **Sécurité** : token Discord via `.env` jamais commité ; API Ollama uniquement en `localhost` par défaut ; aucune interface de commande shell arbitraire depuis Discord ; prévenir les mentions accidentelles `@everyone`/`@here`/utilisateur dans les réponses ; pas de contenu hostile interprété comme instructions de développement.
9. **Interface fournisseur stable, minimale** : `LLMProvider` avec une méthode simple type `generate(prompt, system_prompt, generation_settings) -> str`, implémentation `OllamaProvider`. Ne **pas** implémenter plusieurs fournisseurs pour faire joli ; rendre un second fournisseur possible sans modifier le code Discord. Aucune dépendance ComfyUI en M1.
10. **Exécution très simple** : un README de prise en main et commandes adaptées à Windows PowerShell et Linux/macOS : clone, venv, installation, `.env`, `ollama pull`, lancement. Objectif : contribution GitHub normale, code lisible, peu de dépendances.

## 3. Stack et décisions techniques

- **Python 3.12+** (ou autre version stable explicitement motivée).
- **`discord.py`** et ses application commands. Vérifier la compatibilité réelle `USER_INSTALL` et `PRIVATE_CHANNEL` avec la version fixée des dépendances.
- **`httpx` en mode asynchrone** ou bibliothèque HTTP async légère pour appeler `POST /api/chat` d'Ollama (non-streaming en M1, sauf justification forte). Réutiliser proprement le client HTTP et le fermer à l'arrêt.
- Configuration `.env` avec une solution simple (`python-dotenv` si nécessaire), validation explicite au démarrage.
- **`pytest`** pour les tests ciblés. Pas de linting industriel ni de pipelines compliqués, mais un outil de formatage/lint simple peut être ajouté si cela reste léger.
- **Pas de Docker obligatoire**, base de données, Redis, frontend, système de plugins dynamique, architecture hexagonale surdimensionnée ni télémétrie externe.

### Exemple de configuration souhaitée (adapter seulement si nécessaire)

```dotenv
DISCORD_BOT_TOKEN=replace_me
DISCORD_ALLOWED_USER_IDS=123456789012345678,234567890123456789
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:1.7b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_KEEP_ALIVE=0
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=512
MAX_PROMPT_CHARS=1800
MAX_CONCURRENT_GENERATIONS=1
LLM_SYSTEM_PROMPT=You are a helpful, concise assistant in a Discord friends chat.
LOG_LEVEL=INFO
```

Les valeurs sont **indicatives** : vérifier disponibilité, nom exact et capacité des modèles recommandés au moment de documenter. Ne pas télécharger un modèle automatiquement sans accord. Si le modèle de démonstration proposé n'est pas disponible, substituer un modèle réellement existant et expliciter la substitution. Le nom du modèle est paramétrable. Ne jamais publier de vrai token dans l'exemple.

### Réponses et quotas

- Gérer la limite de longueur des messages Discord (environ 2 000 caractères pour `content`) : découpage propre ou troncature explicite. Éviter le spam de messages multiples ; préférer une politique simple documentée.
- Gérer réponses vides, sortie très longue, indisponibilité du serveur Ollama, modèle manquant, GPU insuffisant, erreur de réseau, timeout, refus Discord, redémarrage, Ctrl+C.
- Refuser poliment les nouvelles générations si l'instance est occupée ; ne jamais laisser se former une file d'attente infinie. Une **limitation de débit légère par utilisateur** peut être envisagée en mémoire si elle est simple et réellement utile.
- Ne jamais exposer les exceptions internes aux utilisateurs Discord ; fournir des messages compréhensibles et des logs techniques expurgés.
- Utiliser `AllowedMentions.none()` ou équivalent vérifié pour sécuriser les réponses.

## 4. Structure envisagée (adapter raisonnablement)

```text
GoatLLM/
  README.md
  LICENSE                      # proposer une licence, ne pas inventer un choix définitif du propriétaire
  .gitignore
  .env.example
  pyproject.toml
  src/goatllm/
    __init__.py
    __main__.py               # python -m goatllm
    config.py
    discord_app.py            # slash commands et rendu
    llm/
      __init__.py
      base.py                 # contrat minimal
      ollama.py               # intégration Ollama
  tests/
    test_config.py
    test_ollama.py
    test_discord_response.py
  docs/
    ARCHITECTURE.md           # court, incluant extensions prévues
    CONTRIBUTING.md           # court, installation et workflow PR
```

N'ajoute pas de fichiers/abstractions inutiles. La génération d'images future pourra vivre dans un module distinct `media/` ou `image_providers/`, mais **ne crée pas aujourd'hui de code ComfyUI fictif ni de dépendance correspondante**. Le code Discord doit rester découplé du transport LLM pour accueillir plus tard images, nouveaux fournisseurs, streaming, application GUI.

## 5. Documentation indispensable

Le README doit être accessible à un ami qui sait utiliser un terminal mais n'a pas suivi le développement. Inclure :

1. Ce qu'est GoatLLM et ce qu'il **n'est pas** (notamment pas un membre de groupe DM, mais une user-installed application accessible par slash command).
2. Procédure de création d'application dans le **Discord Developer Portal**, configuration **User Install**, permissions/scopes nécessaires, disponibilité du contexte **Private Channel**, obtention sûre du token, invitation/installation sur compte, publication des commandes globales et délai éventuel de propagation. Aucun secret dans le dépôt.
3. Installation Python, Ollama, choix du modèle (profils **4 Go VRAM**, **8 Go VRAM**, **CPU**), configuration `.env`, commande de lancement, arrêt propre, dépannage.
4. **Une machine hôte allumée suffit** pour tous les utilisateurs disposant d'un accès autorisé à l'application. Distinguer les ressources de l'hôte des clients Discord. Documenter que plusieurs membres ne lancent **pas** chacun le serveur GoatLLM pour utiliser le même bot.
5. Explications sur les **coûts API nuls pour Ollama local**, mais coûts matériels/électriques, et sur l'impact de `keep_alive`, `num_ctx`, `num_predict`, modèle, quantification et concurrence.
6. Politique de confidentialité : prompt courant transmis à l'instance Ollama de l'hébergeur ; pas de stockage par GoatLLM ; préciser que Discord et l'hébergeur restent des parties impliquées, donc ne pas promettre une confidentialité absolue.
7. Limites actuelles et roadmap : M2 images/ComfyUI, M3 interface desktop et empaquetage, nouveaux fournisseurs optionnels, éventuel contexte conversationnel **opt-in** uniquement à l'avenir.
8. Commandes de tests et guide de contribution court.

## 6. Qualité : suffisamment solide, pas une usine à gaz

- **Tests unitaires isolés** avec HTTP mock, sans nécessiter Discord ni Ollama en production : validation config, payload et réponse Ollama, erreurs/timeout, découpage ou troncature, sécurité mentions, autorisation des utilisateurs.
- **Test manuel d'intégration** guidé dans une vraie conversation privée de groupe Discord (ne pas prétendre le valider sans les identifiants). Documenter une checklist : installation application, disponibilité `/ask`, résultat public, utilisateur non autorisé, Ollama arrêté, prompt trop long, réponses longues, concurrence.
- Vérifier que l'import du module ne démarre ni Discord ni Ollama, et que le nettoyage des ressources intervient à la fermeture.
- Favoriser le typage simple, fonctions courtes, commentaires pour les décisions non évidentes ; ne pas multiplier les wrappers.
- Dépendances épinglées avec une politique raisonnable (versions compatibles et reproductibilité) ; `.gitignore` excluant `.env`, venv, caches et sorties de build.
- Conserver l'interface M1 stable et documentée pour qu'une version « GoatLLM Minimal » demeure maintenable lors de développements futurs, sans lancer maintenant une seconde branche/édition.

## 7. Déroulement demandé à Codex : travailler par jalons

**Jalon A — fondation** : vérifier dossier Git et éventuels fichiers existants (ne pas écraser), créer projet installable, configuration valide, README de base et structure. Résumer brièvement décisions.

**Jalon B — tranche verticale utilisable** : implémenter `/ask`, permissions User Install/Private Channel et fournisseur Ollama, avec erreurs gérées. Il doit être possible de démarrer et tester rapidement.

**Jalon C — robustesse** : contrôles de concurrence, limites, timeouts, mentions, réponse longue, fermeture propre. Ajouter les tests qui prouvent ces points.

**Jalon D — livraison partageable** : compléter README et docs pour vos amis, exemples de configuration, script de lancement uniquement si réellement utile, revue des dépendances et checklist manuelle.

**Important :** après chaque jalon, exécute seulement les tests pertinents, présente un bref bilan des fichiers ajoutés, commandes exécutées, résultats et points manuellement vérifiables. Tu peux faire les jalons successivement dans la même session si le budget le permet, mais **n'enchaîne pas sur la roadmap M2/M3**. Pas de refonte cosmétique massive ni de cycles de tests sans utilité.

## 8. Git et organisation GoatsSoftware

- Nom du projet/dossier/package : **GoatLLM** (`goatllm` côté Python).
- Destination visée : **https://github.com/GoatsSoftware/GoatLLM**. Ne présume pas que le dépôt existe ou que les droits d'écriture sont accordés ; vérifier avant toute opération distante.
- Initialiser Git si ce dossier n'est pas déjà un dépôt. Ne pas écraser l'historique si un dépôt est présent. Faire des commits cohérents pour jalons validés si possible.
- **Ne crée pas de dépôt distant, ne pousse pas sur GitHub, ne crée pas de PR sans approbation explicite.** Préparer les commandes correspondantes, et laisser l'humain décider du moment de publier.
- Ne pas ajouter de token Discord, données utilisateurs, caches/modèles Ollama ou fichiers volumineux au dépôt.
- Documenter un processus de contribution GitHub simple : branche, commit, PR, test.
- Proposer une licence permissive adaptée à une petite organisation open source (MIT par exemple), mais demander la décision du propriétaire avant d'attribuer une licence définitive si non spécifiée.

## 9. Ce qui est explicitement hors M1

- Génération d'images ou GIFs et intégration ComfyUI.
- Mémoire persistante, analyse passive de conversations, historiques, scraping Discord, self-bot.
- GUI Windows, compilateur, setup MSI, auto-updater.
- Agents et tool calling avancés, RAG, accès Internet, MCP, appels à de multiples services.
- Hébergement cloud, Docker orchestration, dashboard de supervision, métriques détaillées.
- Support de 50 utilisateurs simultanés ou haute disponibilité : usage prévu **petit groupe d'amis**.

## 10. Règles de travail et conditions de réussite

- Prends les décisions techniques ordinaires de façon autonome ; **ne m'interromps pas pour des questions mineures**. Explique les choix importants sans discours interminable. Quand l'utilisateur indique ne plus surveiller ton travaille et que tu peux continuer y compris commits et pr merge, fais le jusqu'à la fin de tes crédits sauf milestone ou bug nécessitant un humain.
- Si la version actuelle de la bibliothèque Discord ne permet pas `PRIVATE_CHANNEL` avec la syntaxe attendue, **vérifie la documentation officielle**, ajuste ou propose une alternative conforme ; **n'improvise pas de self-bot**.
- **Ne prétends pas avoir testé sur Discord ou sur un GPU quand tu n'en as pas eu l'accès**. Distingue tests automatisés et vérifications manuelles restantes.
- Ne prétends pas avoir créé ou publié le dépôt GitHub sans avoir réellement effectué l'opération et obtenu confirmation.
- **Succès M1 :** après installation/configuration, une personne lance `python -m goatllm` (ou commande CLI documentée), un utilisateur autorisé invoque `/ask` dans son groupe DM Discord, Ollama génère une réponse textuelle visible aux membres, le bot reste opérationnel en cas d'erreur, et aucune donnée de conversation n'est persistée par GoatLLM.

**Commence maintenant par auditer le dossier courant et la faisabilité exacte Discord + `discord.py`, puis crée le projet en respectant ce brief.**
