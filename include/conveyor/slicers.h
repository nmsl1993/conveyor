// vim:cindent:cino=\:0:et:fenc=utf-8:ff=unix:sw=4:ts=4:

#ifndef SLICERS_H
#define SLICERS_H (1)

#include <QObject>
#include <QString>

#include <json/value.h>

#include <conveyor/fwd.h>

namespace conveyor
{
    /**
       Settings for the Skeinforge and MiracleGrue slicers
     */
    class SlicerConfiguration : public QObject
    {
        Q_OBJECT

    public:
        enum Slicer {
            Skeinforge,
            MiracleGrue
        };

        enum Quality {
            LowQuality,
            MediumQuality,
            HighQuality
        };

        enum Extruder {
            Left,
            Right
        };

        static SlicerConfiguration * defaultConfiguration(Quality quality);

        /// Unpack a configuration serialized to JSON
        SlicerConfiguration(Json::Value &);

        /// Serialize configuration as JSON
        Json::Value toJSON() const;

        Slicer slicer() const;
        QString slicerName() const;

        Extruder extruder() const;
        QString extruderName() const;

        bool raft() const;
        bool supports() const;

        double infill() const;
        double layerHeight() const;
        unsigned shells() const;

        unsigned extruderTemperature() const;
        unsigned platformTemperature() const;

        unsigned printSpeed() const;
        unsigned travelSpeed() const;

    public slots:
        void setSlicer(Slicer slicer);
        void setExtruder(Extruder extruder);

        void setRaft(bool raft);
        void setSupports(bool supports);

        void setInfill(double infill);
        void setLayerHeight(double height);
        void setShells(unsigned shells);

        void setExtruderTemperature(unsigned temperature);
        void setPlatformTemperature(unsigned temperature);

        void setPrintSpeed(unsigned speed);
        void setTravelSpeed(unsigned speed);

    private:
        SlicerConfigurationPrivate * const m_private;
    };
}

#endif
