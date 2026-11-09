"""Manual IP setup with background endpoint detection."""

import asyncio
import ipaddress
import re

import voluptuous as vol
from aiohomekit.exceptions import (
    AccessoryDisconnectedError,
    AlreadyPairedError,
    AuthenticationError,
    BackoffError,
    BusyError,
    MaxPeersError,
    MaxTriesError,
    UnavailableError,
)
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
from .protocol import find_port, pair_direct, sound_candidates, validate_connection


def error_key(error):
    """Translate error types without exposing credentials or raw responses."""
    if isinstance(error, (AlreadyPairedError, UnavailableError, MaxPeersError)):
        return "already_paired"
    if isinstance(error, AuthenticationError):
        return "authentication_failed"
    if isinstance(error, (BackoffError, BusyError, MaxTriesError)):
        return "pairing_busy"
    if isinstance(error, (OSError, TimeoutError, AccessoryDisconnectedError)):
        return "cannot_connect"
    return "cannot_pair"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SoundOptionsFlow()

    def __init__(self):
        self._task = None
        self._input = {}
        self._operation = None
        self._finished = False

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            try:
                host = str(ipaddress.IPv4Address(user_input["host"].strip()))
                pin = re.sub(r"[\s-]", "", user_input["pin"])
                if not re.fullmatch(r"\d{8}", pin):
                    raise ValueError
                self._input = {**user_input, "host": host, "pin": f"{pin[:3]}-{pin[3:5]}-{pin[5:]}"}
                return await self.async_step_connect()
            except ValueError:
                errors["base"] = "invalid_input"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Optional("port", default=0): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=65535)
                    ),
                    vol.Required("pin"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def _connect(self):
        host = self._input["host"]
        port = self._input.get("port", 0) or await find_port(host)
        self._operation = self.hass.async_create_task(pair_direct(host, port, self._input["pin"]))
        data = await asyncio.shield(self._operation)
        return {"host": host, "port": port, "pairing": data}

    async def async_step_connect(self, user_input=None):
        if self._task is None:
            self._task = self.hass.async_create_task(self._connect())
        if not self._task.done():
            return self.async_show_progress(
                step_id="connect", progress_action="connecting", progress_task=self._task
            )
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_finish(self, user_input=None):
        try:
            data = self._task.result()
        except Exception as err:
            # Never log PIN or pairing credentials. Keep the error in the UI.
            self._task = None
            self._input.pop("pin", None)
            return self.async_show_form(
                step_id="retry", data_schema=vol.Schema({}), errors={"base": error_key(err)}
            )
        self._input.pop("pin", None)
        self._finished = True
        await self.async_set_unique_id(data["pairing"]["AccessoryPairingID"].lower())
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="iHome iSS50", data=data)

    async def async_step_retry(self, user_input=None):
        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input=None):
        """Change the endpoint while preserving and verifying the pairing keys."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input:
            try:
                host = str(ipaddress.IPv4Address(user_input["host"].strip()))
                port = int(user_input["port"])
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                errors["base"] = "invalid_endpoint"
            else:
                try:
                    await validate_connection(host, port, entry.data["pairing"])
                except Exception as err:
                    errors["base"] = error_key(err)
                else:
                    return self.async_update_reload_and_abort(
                        entry, data_updates={"host": host, "port": port}
                    )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=entry.data["host"]): str,
                    vol.Required("port", default=entry.data["port"]): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    def async_remove(self):
        # HA invokes this as a synchronous callback after cancelling the progress
        # task. The shielded SRP operation must finish and retain its credentials.
        if not self._finished and self._operation is not None:
            self.hass.async_create_task(self._retain_pairing())

    async def _retain_pairing(self):
        try:
            pairing = await self._operation
        except Exception, asyncio.CancelledError:
            return
        data = {
            "host": pairing["AccessoryIP"],
            "port": pairing["AccessoryPort"],
            "pairing": pairing,
        }
        await self.hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=data
        )

    async def async_step_import(self, user_input):
        await self.async_set_unique_id(user_input["pairing"]["AccessoryPairingID"].lower())
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="iHome iSS50", data=user_input)


class SoundOptionsFlow(config_entries.OptionsFlowWithReload):
    """Select a firmware-specific sound field without modifying pairing keys."""

    async def async_step_init(self, user_input=None):
        entry = self.config_entry
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return self.async_abort(reason="not_loaded")
        choices = {"auto": "Automatic", "disabled": "Disabled"}
        choices.update(sound_candidates(coordinator.accessories))
        errors = {}
        if user_input:
            selected = user_input.get("sound_characteristic", "auto")
            active = user_input.get("sound_active_value", "1")
            if selected not in choices or active not in ("0", "1"):
                errors["base"] = "invalid_sound_mapping"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        **entry.options,
                        "sound_characteristic": selected,
                        "sound_active_value": int(active),
                    },
                )
        current = entry.options.get("sound_characteristic", "auto")
        if current not in choices:
            # Keep an old mapping visible if firmware temporarily omits it.
            choices[current] = f"Previously selected field ({current})"
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("sound_characteristic", default=current): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": key, "label": value} for key, value in choices.items()
                            ]
                        )
                    ),
                    vol.Required(
                        "sound_active_value",
                        default=str(entry.options.get("sound_active_value", 1)),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "1", "label": "1 / true means sound detected"},
                                {"value": "0", "label": "0 / false means sound detected"},
                            ]
                        )
                    ),
                }
            ),
            errors=errors,
        )
