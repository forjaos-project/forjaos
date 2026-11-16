find_package(Qt6 REQUIRED COMPONENTS Core DBus Qml)
qt_add_qml_module(hero_applet_plugin
    URI org.forjaos.hero
    VERSION 1.0
    OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/plasmoid-plugin/org/forjaos/hero"
    PLUGIN_TARGET hero_applet_plugin
    SOURCES hero_service.cpp hero_service.h
)
set_target_properties(hero_applet_plugin PROPERTIES PREFIX "lib")
target_link_libraries(hero_applet_plugin PRIVATE Qt6::Core Qt6::DBus Qt6::Qml)
install(TARGETS hero_applet_plugin LIBRARY DESTINATION lib64/qt6/qml/org/forjaos/hero)
install(FILES "${CMAKE_BINARY_DIR}/plasmoid-plugin/org/forjaos/hero/qmldir"
        DESTINATION lib64/qt6/qml/org/forjaos/hero)
