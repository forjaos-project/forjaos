find_package(Qt6 REQUIRED COMPONENTS Core DBus)
find_package(KF6 REQUIRED COMPONENTS CoreAddons I18n Runner)

kcoreaddons_add_plugin(krunner_forjaos_hero
    SOURCES hero_runner.cpp
    INSTALL_NAMESPACE "kf6/krunner"
)
target_link_libraries(krunner_forjaos_hero PRIVATE
    Qt6::Core
    Qt6::DBus
    KF6::CoreAddons
    KF6::I18n
    KF6::Runner
)
