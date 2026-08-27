import datetime
import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from eventyay.base.models import Event, Organizer, Team, User
from eventyay.plugins.sendmail.forms import TeamMailForm
from eventyay.plugins.sendmail.models import EmailQueue, EmailQueueToUser, ComposingFor


@pytest.fixture
def event():
    o = Organizer.objects.create(name='Dummy', slug='dummy')
    return Event.objects.create(
        organizer=o,
        name='Dummy Event',
        slug='dummy',
        date_from=now(),
        plugins='tests.tickets.testdummy',
    )


@pytest.fixture
def team(event):
    with scopes_disabled():
        t = Team.objects.create(organizer=event.organizer, name='Admin Team', can_change_event_settings=True)
        u1 = User.objects.create_user('alice@dummy.test', 'secret', fullname='Alice Admin')
        u2 = User.objects.create_user('bob@dummy.test', 'secret', fullname='Bob Member')
        t.members.add(u1, u2)
        return t


@pytest.mark.django_db
def test_team_mail_form_initialization(event, team):
    with scopes_disabled():
        form = TeamMailForm(event=event)
        assert 'teams' in form.fields
        assert 'reply_to' in form.fields
        assert 'bcc' in form.fields
        assert 'delivery' in form.fields
        assert 'exclude_me' in form.fields
        assert 'scheduled_at' in form.fields


@pytest.mark.django_db
def test_team_mail_form_delivery_later_requires_scheduled_at(event, team):
    with scopes_disabled():
        data = {
            'teams': [team.pk],
            'subject_0': 'Team Announcement',
            'message_0': 'Hello team',
            'delivery': 'later',
        }
        form = TeamMailForm(data=data, event=event)
        assert not form.is_valid()
        assert 'scheduled_at' in form.errors


@pytest.mark.django_db
def test_team_mail_form_send_now_clears_scheduled_at(event, team):
    with scopes_disabled():
        later = now() + datetime.timedelta(days=1)
        data = {
            'teams': [team.pk],
            'subject_0': 'Team Announcement',
            'message_0': 'Hello team',
            'delivery': 'now',
            'scheduled_at_0': later.strftime('%Y-%m-%d'),
            'scheduled_at_1': later.strftime('%H:%M:%S'),
        }
        form = TeamMailForm(data=data, event=event)
        assert form.is_valid(), form.errors
        assert form.cleaned_data['scheduled_at'] is None


@pytest.mark.django_db
def test_team_mail_form_invalid_bcc(event, team):
    with scopes_disabled():
        data = {
            'teams': [team.pk],
            'subject_0': 'Team Announcement',
            'message_0': 'Hello team',
            'delivery': 'now',
            'bcc': 'invalid-email-address',
        }
        form = TeamMailForm(data=data, event=event)
        assert not form.is_valid()
        assert 'bcc' in form.errors


@pytest.mark.django_db
def test_team_mail_form_valid_bcc(event, team):
    with scopes_disabled():
        data = {
            'teams': [team.pk],
            'subject_0': 'Team Announcement',
            'message_0': 'Hello team',
            'delivery': 'now',
            'bcc': 'valid1@example.com, valid2@example.com',
        }
        form = TeamMailForm(data=data, event=event)
        assert form.is_valid(), form.errors
