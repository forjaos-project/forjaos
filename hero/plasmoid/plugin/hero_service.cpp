#include "hero_service.h"

#include <QDBusConnection>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QDBusVariant>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>

HeroService::HeroService(QObject *parent)
    : QObject(parent)
    , m_hero(QStringLiteral("org.forjaos.Hero"), QStringLiteral("/org/forjaos/Hero"),
             QStringLiteral("org.forjaos.Hero"), QDBusConnection::sessionBus())
{
    updateState();
    QDBusConnection::sessionBus().connect(QStringLiteral("org.forjaos.Hero"),
                                          QStringLiteral("/org/forjaos/Hero"),
                                          QStringLiteral("org.forjaos.Hero"),
                                          QStringLiteral("StateChanged"), this,
                                          SLOT(stateChangedFromBus(QString)));
    QDBusConnection::sessionBus().connect(QStringLiteral("org.forjaos.Hero"),
                                          QStringLiteral("/org/forjaos/Hero"),
                                          QStringLiteral("org.freedesktop.DBus.Properties"),
                                          QStringLiteral("PropertiesChanged"), this,
                                          SLOT(propertiesChangedFromBus(QString,QVariantMap,QStringList)));
}

QString HeroService::state() const { return m_state; }
QString HeroService::lastAnswer() const { return m_lastAnswer; }
bool HeroService::busy() const { return m_busy; }
bool HeroService::microphoneEnabled() const { return m_microphoneEnabled; }

void HeroService::toggleMicrophone()
{
    QDBusInterface properties(QStringLiteral("org.forjaos.Hero"), QStringLiteral("/org/forjaos/Hero"),
                              QStringLiteral("org.freedesktop.DBus.Properties"), QDBusConnection::sessionBus());
    auto *watcher = new QDBusPendingCallWatcher(
        properties.asyncCall(QStringLiteral("Set"), QStringLiteral("org.forjaos.Hero"),
                             QStringLiteral("MicrophoneEnabled"),
                             QVariant::fromValue(QDBusVariant(!m_microphoneEnabled))), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [this, watcher]() {
        updateState();
        watcher->deleteLater();
    });
}

void HeroService::propertiesChangedFromBus(const QString &interface, const QVariantMap &changed,
                                            const QStringList &invalidated)
{
    if (interface != QLatin1String("org.forjaos.Hero")) return;
    if (changed.contains(QStringLiteral("MicrophoneEnabled"))) {
        const bool next = changed.value(QStringLiteral("MicrophoneEnabled")).toBool();
        if (m_microphoneEnabled != next) {
            m_microphoneEnabled = next;
            Q_EMIT microphoneEnabledChanged();
        }
    } else if (invalidated.contains(QStringLiteral("MicrophoneEnabled"))) {
        updateState();
    }
}

void HeroService::openOverlay()
{
    QProcess::startDetached(QStringLiteral("/usr/libexec/forjaos/hero-overlay"), {});
}

void HeroService::askText(const QString &prompt)
{
    const QString query = prompt.trimmed();
    if (query.isEmpty() || query.size() > 4096 || m_busy) {
        return;
    }
    if (!m_hero.isValid()) {
        m_lastAnswer = tr("HERO indisponível nesta sessão.");
        Q_EMIT answerChanged();
        return;
    }

    m_busy = true;
    Q_EMIT busyChanged();
    auto *watcher = new QDBusPendingCallWatcher(
        m_hero.asyncCall(QStringLiteral("AskText"), query, QDir::homePath(), QStringLiteral("{}")), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [this, watcher]() {
        QDBusPendingReply<QString> reply = *watcher;
        if (reply.isError()) {
            m_lastAnswer = tr("Não foi possível consultar o HERO: %1").arg(reply.error().message());
        } else {
            const auto response = QJsonDocument::fromJson(reply.value().toUtf8()).object();
            m_lastAnswer = response.value(QStringLiteral("answer")).toString(
                tr("O HERO não retornou uma resposta legível."));
            if (response.value(QStringLiteral("status")).toString() == QLatin1String("confirmation_required")) {
                m_lastAnswer += tr(" Envie novamente a solicitação na Central de Comando para revisá-la.");
            }
        }
        watcher->deleteLater();
        m_busy = false;
        updateState();
        Q_EMIT answerChanged();
        Q_EMIT busyChanged();
    });
}

void HeroService::stateChangedFromBus(const QString &state)
{
    if (m_state != state) {
        m_state = state;
        Q_EMIT stateChanged();
    }
}

void HeroService::updateState()
{
    const QString next = m_hero.isValid() ? m_hero.property("State").toString() : QStringLiteral("indisponível");
    stateChangedFromBus(next);
    const bool microphone = m_hero.isValid() && m_hero.property("MicrophoneEnabled").toBool();
    if (m_microphoneEnabled != microphone) {
        m_microphoneEnabled = microphone;
        Q_EMIT microphoneEnabledChanged();
    }
}
