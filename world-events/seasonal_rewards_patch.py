"""Seasonal gold for the original city commissions. The stored contract value stays the base."""

# All nine sites load the same field. Keep the eight offer/report/list displays consistent
# with the city hall settlement and only credit gold in the original settlement routine.
REWARD_SITES = {
    0x44806B: ("edi", "edx"),
    0x448123: ("edi", "edx"),
    0x448160: ("edi", "edx"),
    0x4481DF: ("edi", "ecx"),
    0x4494F6: ("ebx", "edx"),
    0x44952B: ("ebx", "edx"),
    0x44956A: ("ebx", "eax"),
    0x44958F: ("ebx", "eax"),
    0x44B259: ("esi", "edx"),
}


def emit(put, asm, address, patch):
    amount = put(asm("""
      push ebx; push ecx; push edx; mov ebx,[esp+16];
      mov ecx,0x48d380; call 0x4466e0;
      mov edx,[ebx+0x124]; test edx,edx; jle done;
      cmp dword ptr [ebx+4],1; je delivery;
      cmp dword ptr [ebx+4],0; jne done;
      cmp eax,1; je twice; cmp eax,7; je twice; jmp limit;
    delivery:
      cmp eax,5; je twice; cmp eax,11; jne limit;
    twice:
      add edx,edx; jno limit; mov edx,0x7fffffff;
    limit:
      mov ecx,dword ptr [0x46e5d8]; test ecx,ecx; js done;
      mov eax,0x7fffffff; sub eax,ecx; cmp edx,eax; jbe done; mov edx,eax;
    done:
      mov eax,edx; pop edx; pop ecx; pop ebx; ret 4
    """, address()))
    for site, (quest, result) in REWARD_SITES.items():
        original = asm(f"mov {result},[{quest}+0x124]", site)
        save = "push eax;" if result != "eax" else ""
        restore = f"mov {result},eax; pop eax;" if result != "eax" else ""
        shim = put(asm(f"""
          pushfd; {save} push {quest}; call {amount}; {restore}
          popfd; jmp {site + len(original)}
        """, address()))
        patch(site, original, asm(f"jmp {shim}", site) + bytes([0x90]) * (len(original)-5))
    return dict(seasonal_rewards=dict(native_commission_amount=hex(amount),
                delivery_months=[5,11], recapture_months=[1,7],
                native_reward_sites=[hex(site) for site in REWARD_SITES]))
