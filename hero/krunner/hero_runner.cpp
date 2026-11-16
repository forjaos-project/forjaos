#include <KRunner/AbstractRunner>
#include <KRunner/QueryMatch>
#include <KRunner/RunnerContext>
#include <KRunner/RunnerSyntax>
#include <KPluginFactory>
#include <KLocalizedString>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDir>
#include <QVariantList>

class HeroRunner final : public KRunner::AbstractRunner
{
    Q_OBJECT

public:
    HeroRunner(QObject *parent, const KPluginMetaData &metadata)
        : KRunner::AbstractRunner(parent, metadata)
    {
        setSyntaxes({
            KRunner::RunnerSyntax(QStringLiteral("h :q:"), i18n("Enviar uma consulta ao HERO: :q:")),
            KRunner::RunnerSyntax(QStringLiteral(":q:"), i18n("Perguntar ao HERO em linguagem natural: :q:")),
        });
    }

    void match(KRunner::RunnerContext &context) override
    {
        const QString input = context.query().trimmed();
        const bool explicitPrefix = input.startsWith(QLatin1String("h "), Qt::CaseInsensitive);
        if (input.isEmpty() || input.compare(QLatin1String("h"), Qt::CaseInsensitive) == 0) {
            return;
        }

        const QString prompt = explicitPrefix ? input.mid(2).trimmed() : input;
        if (prompt.isEmpty() || !context.isValid()) {
            return;
        }

        KRunner::QueryMatch result(this);
        result.setId(QStringLiteral("hero:") + prompt);
        result.setText(i18n("Enviar ao HERO: %1", prompt));
        result.setSubtext(i18n("O Policy Engine valida ações e pede confirmação quando necessário"));
        result.setIconName(QStringLiteral("assistant"));
        result.setData(prompt);
        result.setRelevance(explicitPrefix ? 1.0 : 0.35);
        if (explicitPrefix) {
            result.setCategoryRelevance(KRunner::QueryMatch::CategoryRelevance::Highest);
        }
        context.addMatch(result);
    }

    void run(const KRunner::RunnerContext &, const KRunner::QueryMatch &match) override
    {
        const QString prompt = match.data().toString();
        if (prompt.isEmpty()) {
            return;
        }
        if (prompt.size() > 4096) {
            notify(i18n("Consulta muito longa"), i18n("Limite de 4096 caracteres."));
            return;
        }

        auto *hero = new QDBusInterface(QStringLiteral("org.forjaos.Hero"),
                                        QStringLiteral("/org/forjaos/Hero"),
                                        QStringLiteral("org.forjaos.Hero"),
                                        QDBusConnection::sessionBus(), this);
        if (!hero->isValid()) {
            notify(i18n("HERO indisponível"), i18n("Inicie a sessão ForjaOS e tente novamente."));
            hero->deleteLater();
            return;
        }

        const auto call = hero->asyncCall(QStringLiteral("AskText"), prompt, QDir::homePath(), QStringLiteral("{}"));
        auto *watcher = new QDBusPendingCallWatcher(call, hero);
        connect(watcher, &QDBusPendingCallWatcher::finished, this, [watcher, hero]() {
            QDBusPendingReply<QString> reply = *watcher;
            if (reply.isError()) {
                notify(i18n("Falha ao consultar o HERO"), reply.error().message());
            } else {
                const QJsonObject response = QJsonDocument::fromJson(reply.value().toUtf8()).object();
                const QString answer = response.value(QStringLiteral("answer")).toString(
                    i18n("O HERO não retornou uma resposta legível."));
                const bool needsConfirmation = response.value(QStringLiteral("status")).toString()
                    == QLatin1String("confirmation_required");
                notify(needsConfirmation ? i18n("Confirmação necessária") : i18n("Resposta do HERO"),
                       needsConfirmation
                           ? i18n("Envie novamente a solicitação na Central de Comando para revisar a ação.")
                           : answer);
            }
            watcher->deleteLater();
            hero->deleteLater();
        });
    }

private:
    static void notify(const QString &title, const QString &body)
    {
        QDBusMessage message = QDBusMessage::createMethodCall(
            QStringLiteral("org.freedesktop.Notifications"), QStringLiteral("/org/freedesktop/Notifications"),
            QStringLiteral("org.freedesktop.Notifications"), QStringLiteral("Notify"));
        message << QStringLiteral("HERO") << uint(0) << QStringLiteral("assistant") << title << body
                << QStringList{} << QVariantMap{} << 7000;
        QDBusConnection::sessionBus().asyncCall(message);
    }
};

K_PLUGIN_CLASS_WITH_JSON(HeroRunner, "plasma-runner-hero.json")

#include "hero_runner.moc"
