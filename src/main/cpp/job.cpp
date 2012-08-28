// vim:cindent:cino=\:0:et:fenc=utf-8:ff=unix:sw=4:ts=4:

#include <QUuid>
#include <QDebug>
#include <QScopedPointer>

#include <conveyor.h>

#include "conveyorprivate.h"
#include "jobprivate.h"
#include "printerprivate.h"

namespace conveyor
{
    Job::Job
        ( Conveyor * conveyor
        , Printer * printer
        , int const & id
        )
        : m_private
          ( new JobPrivate (conveyor, this, printer, id)
          )
    {
    }

    Job::~Job (void)
    {
    }

    int
    Job::id (void) const
    {
        return m_private->m_id;
    }

    QString
    Job::name (void) const
    {
        return m_private->m_name;
    }

    JobState
    Job::jobState (void) const
    {
        return m_private->m_state;
    }

    JobConclusion
    Job::jobConclusion (void) const
    {
        return m_private->m_conclusion;
    }

    int
    Job::currentStepProgress (void) const
    {
        return m_private->m_currentStepProgress;
    }

    QString
    Job::currentStepName (void) const
    {
        return m_private->m_currentStepName;
    }

    void
    Job::emitChanged (void)
    {
        emit changed();
    }
}
