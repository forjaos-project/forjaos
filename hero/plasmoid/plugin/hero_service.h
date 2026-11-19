#pragma once

#include <QObject>
#include <QDBusInterface>
#include <QVariantMap>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

class HeroService : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(QString lastAnswer READ lastAnswer NOTIFY answerChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(bool microphoneEnabled READ microphoneEnabled NOTIFY microphoneEnabledChanged)

public:
    explicit HeroService(QObject *parent = nullptr);
    QString state() const;
    QString lastAnswer() const;
    bool busy() const;
    bool microphoneEnabled() const;

    Q_INVOKABLE void openOverlay();
    Q_INVOKABLE void askText(const QString &prompt);
    Q_INVOKABLE void toggleMicrophone();

Q_SIGNALS:
    void stateChanged();
    void answerChanged();
    void busyChanged();
    void microphoneEnabledChanged();

private Q_SLOTS:
    void stateChangedFromBus(const QString &state);
    void propertiesChangedFromBus(const QString &interface, const QVariantMap &changed, const QStringList &invalidated);

private:
    void updateState();

    QDBusInterface m_hero;
    QString m_state = QStringLiteral("indisponível");
    QString m_lastAnswer;
    bool m_busy = false;
    bool m_microphoneEnabled = false;
};
